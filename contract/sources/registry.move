module hansen::registry {
    use std::signer;
    use std::vector;
    use std::error;
    use aptos_framework::table::{Self, Table};
    use aptos_framework::event::{Self, EventHandle};
    use aptos_framework::account;

    // Error codes
    const E_NOT_INITIALIZED: u64 = 1;
    const E_ALREADY_INITIALIZED: u64 = 2;
    const E_NOT_AUTHORIZED: u64 = 3;
    const E_EMPTY_BLOB_NAME: u64 = 4;

    struct SnapshotRecord has store, drop, copy {
        blob_name: vector<u8>,
        merkle_root: vector<u8>,
        timestamp: u64,
        data_type: vector<u8>,
        record_count: u64,
    }

    struct SnapshotRecordedEvent has drop, store {
        record_id: u64,
        blob_name: vector<u8>,
        timestamp: u64,
        data_type: vector<u8>,
    }

    struct Registry has key {
        records: Table<u64, SnapshotRecord>,
        total_records: u64,
        snapshot_events: EventHandle<SnapshotRecordedEvent>,
    }

    /// Initializes the Registry under the signer account
    public entry fun initialize(admin: &signer) {
        let admin_addr = signer::address_of(admin);
        assert!(!exists<Registry>(admin_addr), error::already_exists(E_ALREADY_INITIALIZED));

        let registry = Registry {
            records: table::new(),
            total_records: 0,
            snapshot_events: account::new_event_handle<SnapshotRecordedEvent>(admin),
        };
        move_to(admin, registry);
    }

    /// Records a new snapshot / depth archive attestation on-chain
    public entry fun record_snapshot(
        admin: &signer,
        blob_name: vector<u8>,
        merkle_root: vector<u8>,
        timestamp: u64,
        data_type: vector<u8>,
        record_count: u64,
    ) acquires Registry {
        let admin_addr = signer::address_of(admin);
        assert!(exists<Registry>(admin_addr), error::not_found(E_NOT_INITIALIZED));
        assert!(vector::length(&blob_name) > 0, error::invalid_argument(E_EMPTY_BLOB_NAME));

        let registry = borrow_global_mut<Registry>(admin_addr);
        let record_id = registry.total_records + 1;

        let record = SnapshotRecord {
            blob_name: copy blob_name,
            merkle_root,
            timestamp,
            data_type: copy data_type,
            record_count,
        };

        table::add(&mut registry.records, record_id, record);
        registry.total_records = record_id;

        event::emit_event(
            &mut registry.snapshot_events,
            SnapshotRecordedEvent {
                record_id,
                blob_name,
                timestamp,
                data_type,
            },
        );
    }

    #[view]
    public fun is_initialized(addr: address): bool {
        exists<Registry>(addr)
    }

    #[view]
    public fun get_total_records(addr: address): u64 acquires Registry {
        if (!exists<Registry>(addr)) {
            0
        } else {
            let registry = borrow_global<Registry>(addr);
            registry.total_records
        }
    }

    #[view]
    public fun get_snapshot_record(addr: address, record_id: u64): (vector<u8>, vector<u8>, u64, vector<u8>, u64) acquires Registry {
        assert!(exists<Registry>(addr), error::not_found(E_NOT_INITIALIZED));
        let registry = borrow_global<Registry>(addr);
        let record = table::borrow(&registry.records, record_id);
        (
            *&record.blob_name,
            *&record.merkle_root,
            record.timestamp,
            *&record.data_type,
            record.record_count,
        )
    }
}
