import crypto from "crypto";
import fs from "fs";

export const IV_LENGTH = 12;
export const TAG_LENGTH = 16;
export const AAD_PREFIX = "hansen_depth_v1";

export function getOrCreateKey(keyHex?: string): Buffer {
  if (keyHex && keyHex.length === 64) {
    return Buffer.from(keyHex, "hex");
  }
  return crypto.randomBytes(32);
}

export function encryptDepthPayload(
  data: Buffer,
  keyBuffer?: Buffer
): { encryptedPayload: Buffer; keyHex: string } {
  const key = keyBuffer ?? crypto.randomBytes(32);
  const iv = crypto.randomBytes(IV_LENGTH);

  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(Buffer.from(AAD_PREFIX, "utf8"));

  const ciphertext = Buffer.concat([cipher.update(data), cipher.final()]);
  const tag = cipher.getAuthTag();

  const encryptedPayload = Buffer.concat([iv, tag, ciphertext]);
  return {
    encryptedPayload,
    keyHex: key.toString("hex"),
  };
}

export function decryptDepthPayload(
  packed: Buffer,
  keyHex: string
): Buffer {
  if (packed.length < IV_LENGTH + TAG_LENGTH) {
    throw new Error("Payload too short to contain IV and AuthTag");
  }

  const key = Buffer.from(keyHex, "hex");
  const iv = packed.subarray(0, IV_LENGTH);
  const tag = packed.subarray(IV_LENGTH, IV_LENGTH + TAG_LENGTH);
  const ciphertext = packed.subarray(IV_LENGTH + TAG_LENGTH);

  const decipher = crypto.createDecipheriv("aes-256-gcm", key, iv);
  decipher.setAAD(Buffer.from(AAD_PREFIX, "utf8"));
  decipher.setAuthTag(tag);

  return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
}

export async function encryptDepthPayloadOptimized(
  inputPath: string,
  keyBuffer?: Buffer
): Promise<{ encryptedPayload: Buffer; keyHex: string; originalSize: number }> {
  const stat = fs.statSync(inputPath);
  const origSize = stat.size;
  const key = keyBuffer ?? crypto.randomBytes(32);
  const iv = crypto.randomBytes(IV_LENGTH);

  const outBuffer = Buffer.allocUnsafe(IV_LENGTH + TAG_LENGTH + origSize);
  iv.copy(outBuffer, 0);

  const cipher = crypto.createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(Buffer.from(AAD_PREFIX, "utf8"));

  let writeOffset = IV_LENGTH + TAG_LENGTH;

  return new Promise((resolve, reject) => {
    const stream = fs.createReadStream(inputPath, { highWaterMark: 1024 * 1024 });

    stream.on("data", (chunk: Buffer | string) => {
      const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      const enc = cipher.update(buf);
      enc.copy(outBuffer, writeOffset);
      writeOffset += enc.length;
    });

    stream.on("end", () => {
      try {
        const finalChunk = cipher.final();
        if (finalChunk.length > 0) {
          finalChunk.copy(outBuffer, writeOffset);
          writeOffset += finalChunk.length;
        }
        const tag = cipher.getAuthTag();
        tag.copy(outBuffer, IV_LENGTH);

        resolve({
          encryptedPayload: outBuffer,
          keyHex: key.toString("hex"),
          originalSize: origSize,
        });
      } catch (err) {
        reject(err);
      }
    });

    stream.on("error", reject);
  });
}
