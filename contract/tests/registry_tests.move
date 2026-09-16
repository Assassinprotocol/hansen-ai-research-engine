#[test_only]
module hansen::registry_tests {
    use std::signer;
    use aptos_framework::account;
    use hansen::registry;

    #[test(admin = @hansen)]
    fun test_initialize_and_record(admin: &signer) {
        account::create_account_for_test(signer::address_of(admin));
        
        // 1. Test initialize
        assert!(!registry::is_initialized(signer::address_of(admin)), 101);
        registry::initialize(admin);
        assert!(registry::is_initialized(signer::address_of(admin)), 102);
        assert!(registry::get_total_records(signer::address_of(admin)) == 0, 103);

        // 2. Test record snapshot
        let blob_name = b"hansen_ai/market_pipeline/snapshots/snapshot_20260916_202327.json";
        let merkle_root = b"0xabcdef1234567890";
        let timestamp = 1789570000;
        let data_type = b"snapshot";
        let record_count = 718;

        registry::record_snapshot(
            admin,
            blob_name,
            merkle_root,
            timestamp,
            data_type,
            record_count
        );

        assert!(registry::get_total_records(signer::address_of(admin)) == 1, 104);

        // 3. Test record second item (depth archive)
        let depth_name = b"hansen_ai/market_pipeline/depth/depth_2026-09-15.tar.gz";
        let depth_merkle = b"0x9876543210fedcba";
        let depth_ts = 1789574000;
        let depth_type = b"depth";
        let depth_count = 648;

        registry::record_snapshot(
            admin,
            depth_name,
            depth_merkle,
            depth_ts,
            depth_type,
            depth_count
        );

        assert!(registry::get_total_records(signer::address_of(admin)) == 2, 105);

        // 4. Verify record content
        let (name, merkle, ts, dtype, count) = registry::get_snapshot_record(signer::address_of(admin), 1);
        assert!(name == blob_name, 106);
        assert!(merkle == merkle_root, 107);
        assert!(ts == timestamp, 108);
        assert!(dtype == data_type, 109);
        assert!(count == record_count, 110);
    }

    #[test(admin = @hansen)]
    #[expected_failure(abort_code = 524290, location = hansen::registry)] // error::already_exists(E_ALREADY_INITIALIZED)
    fun test_double_initialize_fails(admin: &signer) {
        account::create_account_for_test(signer::address_of(admin));
        registry::initialize(admin);
        registry::initialize(admin); // Should abort
    }

    #[test(admin = @hansen)]
    #[expected_failure(abort_code = 65540, location = hansen::registry)] // error::invalid_argument(E_EMPTY_BLOB_NAME)
    fun test_empty_blob_name_fails(admin: &signer) {
        account::create_account_for_test(signer::address_of(admin));
        registry::initialize(admin);
        registry::record_snapshot(
            admin,
            b"", // Empty blob name
            b"0xabc",
            1789570000,
            b"snapshot",
            718
        );
    }
}
