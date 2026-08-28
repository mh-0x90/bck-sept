CREATE TABLE IF NOT EXISTS reference_values (
    category TEXT NOT NULL,
    value TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (category, value)
);

CREATE TABLE IF NOT EXISTS flow_records (
    id TEXT PRIMARY KEY,
    flow_type TEXT NOT NULL CHECK (flow_type IN ('shipment', 'label', 'pickup', 'customs', 'delivery')),
    stage SMALLINT NOT NULL DEFAULT 1 CHECK (stage BETWEEN 1 AND 10),
    status TEXT NOT NULL DEFAULT 'ready',
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO reference_values (category, value, meta) VALUES
('country', 'DE', '{}'),
('country', 'FR', '{}'),
('country', 'NL', '{}'),
('currency', 'EUR', '{}'),
('service', 'express', '{"max_weight": 30}'),
('service', 'standard', '{"max_weight": 50}'),
('carrier', 'NorthLine', '{}'),
('carrier', 'RoadPost', '{}'),
('label_format', 'A6', '{}'),
('handoff_method', 'door', '{}'),
('handoff_method', 'reception', '{}'),
('handoff_method', 'locker', '{}'),
('location_type', 'address', '{}'),
('location_type', 'locker', '{}'),
('service_carrier', 'express:NorthLine', '{}'),
('service_carrier', 'standard:RoadPost', '{}'),
('handoff_location', 'door:address', '{}'),
('handoff_location', 'reception:address', '{}'),
('handoff_location', 'locker:locker', '{}')
ON CONFLICT DO NOTHING;

INSERT INTO flow_records (id, flow_type, payload) VALUES
('PKG-4821', 'shipment', '{
  "kind":"Shipment",
  "tracking":"PKG-4821",
  "sender":"Pine Works",
  "recipient":"Mira Keller",
  "destination":"Berlin",
  "country":"DE",
  "postal_code":"10115",
  "weight_kg":2.4,
  "length_cm":38,
  "width_cm":24,
  "height_cm":14,
  "service":"express",
  "carrier":"NorthLine"
}'),
('LBL-2087', 'label', '{
  "kind":"Shipping label",
  "shipment_ref":"PKG-4821",
  "format":"A6",
  "carrier":"NorthLine",
  "service":"express",
  "tracking":"PKG-4821",
  "route_code":"BER-14"
}'),
('PUP-7314', 'pickup', '{
  "kind":"Pickup booking",
  "pickup_ref":"PUP-7314",
  "contact":"Lea Meyer",
  "location":"Warehouse 4, Berlin",
  "window_start":"09:00",
  "window_end":"12:00",
  "parcel_count":3,
  "service":"express",
  "carrier":"NorthLine"
}'),
('CUS-5526', 'customs', '{
  "kind":"Customs declaration",
  "declaration_ref":"CUS-5526",
  "exporter":"Pine Works",
  "importer":"Atelier Nord",
  "destination_country":"FR",
  "currency":"EUR",
  "items":[
    {"description":"Canvas pouch","quantity":2,"unit_value":18.50,"hs_code":"420292"},
    {"description":"Cotton strap","quantity":1,"unit_value":9.00,"hs_code":"630790"}
  ],
  "total_value":46.00
}'),
('DLV-8842', 'delivery', '{
  "kind":"Delivery confirmation",
  "tracking":"PKG-4821",
  "recipient":"Mira Keller",
  "location":"24 Lindenstrasse, Berlin",
  "location_type":"address",
  "method":"door",
  "delivered_on":"2026-08-20",
  "carrier":"NorthLine",
  "proof_ref":"POD-8842"
}')
ON CONFLICT (id) DO NOTHING;
