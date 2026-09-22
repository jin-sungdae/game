CREATE TABLE game.m_item (
 item_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 item_code varchar(40) NOT NULL UNIQUE,
 item_name varchar(100) NOT NULL,
 item_type varchar(32) NOT NULL CHECK(item_type IN ('BATTLE_CONSUMABLE','COMPANION_CONSUMABLE')),
 price bigint NOT NULL CHECK(price>0), max_stack integer NOT NULL CHECK(max_stack>0),
 use_yn boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO game.m_item(item_code,item_name,item_type,price,max_stack) VALUES
 ('SMALL_POTION','Small Potion','BATTLE_CONSUMABLE',20,99),
 ('BOND_BERRY','Bond Berry','COMPANION_CONSUMABLE',30,99),
 ('CAPTURE_CHARM','Capture Charm','BATTLE_CONSUMABLE',40,99);
CREATE TABLE game.t_inventory (
 inventory_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 player_id bigint NOT NULL REFERENCES game.t_player,
 item_id bigint NOT NULL REFERENCES game.m_item,
 quantity integer NOT NULL CHECK(quantity>=0),
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(player_id,item_id)
);
CREATE INDEX ix_inventory_item ON game.t_inventory(item_id);
CREATE TABLE game.t_item_purchase (
 purchase_id uuid PRIMARY KEY, player_id bigint NOT NULL REFERENCES game.t_player,
 item_id bigint NOT NULL REFERENCES game.m_item,
 quantity integer NOT NULL CHECK(quantity>0), unit_price bigint NOT NULL CHECK(unit_price>0),
 total_price bigint NOT NULL CHECK(total_price>0 AND total_price::numeric=quantity::numeric*unit_price),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_purchase_player ON game.t_item_purchase(player_id,created_at);
CREATE INDEX ix_purchase_item ON game.t_item_purchase(item_id);
CREATE TABLE game.t_battle_item_effect (
 battle_id uuid NOT NULL REFERENCES game.t_battle,
 effect_type varchar(32) NOT NULL CHECK(effect_type='CAPTURE_BONUS'),
 value numeric(4,3) NOT NULL CHECK(value>0 AND value<=1),
 consumed_at timestamptz, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(battle_id,effect_type),
 CHECK(consumed_at IS NULL OR consumed_at>=created_at)
);
