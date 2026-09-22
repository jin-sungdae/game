//! Item wire contracts and request/presentation guards; effects are never calculated locally.
use super::{
    battle::{Battle, Command, Status},
    Api,
};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ShopItem {
    pub item_code: String,
    pub item_name: String,
    pub item_type: String,
    pub price: u64,
    pub owned_quantity: u32,
    pub max_stack: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Owned {
    pub item_code: String,
    pub item_name: String,
    pub item_type: String,
    pub quantity: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Purchase {
    pub purchase_id: Uuid,
    pub item_code: String,
    pub quantity: u32,
    pub unit_price: u64,
    pub total_price: u64,
    pub gold_after: u64,
    pub remaining_quantity: u32,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Used {
    pub item_code: String,
    pub remaining_quantity: u32,
    pub healed_amount: Option<u32>,
    pub current_hp: Option<u32>,
    pub max_hp: Option<u32>,
    pub bond_before: Option<u32>,
    pub bond_after: Option<u32>,
    pub armed: Option<bool>,
    pub bonus: Option<f64>,
    pub battle_id: Option<Uuid>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Effect {
    pub battle_id: Uuid,
    pub effect_type: String,
    pub value: f64,
    pub armed: bool,
    pub consumed_at: Option<String>,
}
#[derive(Clone, Debug, Default, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Inventory {
    pub gold: u64,
    pub shop: Vec<ShopItem>,
    pub owned: Vec<Owned>,
    pub effects: Vec<Effect>,
}
#[derive(Clone, Debug, Default, Serialize)]
pub struct Presentation {
    pub inventory: Option<Inventory>,
    pub busy: bool,
    pub error: Option<String>,
    pub feedback: Option<String>,
}
pub fn supported(code: &str) -> bool {
    matches!(code, "SMALL_POTION" | "BOND_BERRY" | "CAPTURE_CHARM")
}
impl Presentation {
    pub fn command(&mut self, action: &str, battle: Option<&Battle>) -> Option<Command> {
        if self.busy {
            return None;
        }
        let command = match action {
            "shop" | "inventory" | "battle-items" | "items-refresh" => {
                Command::LoadItems(battle.map(|b| b.battle_id))
            }
            _ => {
                let (verb, code) = action.split_once(':')?;
                if !supported(code) {
                    return None;
                }
                match verb {
                    "buy" => Command::Purchase(code.into()),
                    "use" => {
                        let active = battle.filter(|b| {
                            b.status == Status::Active && b.encounter_status == "ACTIVE"
                        });
                        let id = if code == "BOND_BERRY" {
                            if active.is_some() {
                                return None;
                            }
                            None
                        } else {
                            Some(active?.battle_id)
                        };
                        Command::UseItem(code.into(), id)
                    }
                    _ => return None,
                }
            }
        };
        self.busy = true;
        self.error = None;
        self.feedback = None;
        Some(command)
    }
    pub fn finish(&mut self, error: Option<String>) {
        self.busy = false;
        self.error = error;
    }
    pub fn purchase(&mut self, value: Purchase) {
        if let Some(i) = &mut self.inventory {
            i.gold = value.gold_after;
            for item in &mut i.shop {
                if item.item_code == value.item_code {
                    item.owned_quantity = value.remaining_quantity;
                }
            }
            for item in &mut i.owned {
                if item.item_code == value.item_code {
                    item.quantity = value.remaining_quantity;
                }
            }
        }
        self.feedback = Some(format!(
            "Purchased {} ×{} · {} G",
            value.item_code, value.quantity, value.total_price
        ));
    }
    pub fn used(&mut self, value: &Used) {
        if let Some(i) = &mut self.inventory {
            for item in &mut i.owned {
                if item.item_code == value.item_code {
                    item.quantity = value.remaining_quantity;
                }
            }
            for item in &mut i.shop {
                if item.item_code == value.item_code {
                    item.owned_quantity = value.remaining_quantity;
                }
            }
        }
        self.feedback = Some(if let Some(heal) = value.healed_amount {
            format!("HP +{heal}")
        } else if let (Some(before), Some(after)) = (value.bond_before, value.bond_after) {
            format!("Bond {before} → {after} ♥")
        } else {
            "Charm Ready".into()
        });
    }
}
impl Api {
    pub fn items(&self, id: Option<Uuid>) -> Result<Inventory, &'static str> {
        let shop: Vec<ShopItem> = self
            .request("/api/v1/shop/items", false)?
            .ok_or("missing shop")?;
        let owned: Vec<Owned> = self
            .request("/api/v1/inventory", false)?
            .ok_or("missing inventory")?;
        let effects: Vec<Effect> = if let Some(id) = id {
            self.request(&format!("/api/v1/battles/{id}/item-effects"), false)?
                .ok_or("missing item effects")?
        } else {
            vec![]
        };
        if shop.len() > 128
            || owned.len() > 128
            || effects.len() > 16
            || shop.iter().any(|i| {
                i.item_code.is_empty()
                    || i.price == 0
                    || i.max_stack == 0
                    || i.owned_quantity > i.max_stack
            })
            || owned.iter().any(|i| i.item_code.is_empty())
            || effects.iter().any(|e| {
                Some(e.battle_id) != id
                    || !e.value.is_finite()
                    || e.value <= 0.0
                    || e.value > 1.0
                    || e.armed == e.consumed_at.is_some()
            })
        {
            return Err("invalid inventory response");
        }
        Ok(Inventory {
            gold: self.bootstrap()?.player.gold,
            shop,
            owned,
            effects,
        })
    }
    pub fn purchase(&self, code: &str, quantity: u32) -> Result<Purchase, &'static str> {
        if !supported(code) || quantity == 0 {
            return Err("invalid item command");
        }
        let p: Purchase = self
            .request_json(
                "/api/v1/shop/purchases",
                Some(&serde_json::json!({"itemCode":code,"quantity":quantity})),
            )?
            .ok_or("missing purchase")?;
        if p.purchase_id.is_nil()
            || p.item_code != code
            || p.quantity != quantity
            || p.unit_price == 0
            || p.unit_price.checked_mul(p.quantity as u64) != Some(p.total_price)
        {
            return Err("invalid purchase response");
        }
        Ok(p)
    }
    pub fn use_item(&self, code: &str, id: Option<Uuid>) -> Result<Used, &'static str> {
        if !supported(code) {
            return Err("invalid item command");
        }
        let u: Used = self
            .request_json(
                &format!("/api/v1/inventory/items/{code}/use"),
                Some(&serde_json::json!({"battleId":id})),
            )?
            .ok_or("missing item result")?;
        if u.item_code != code || u.battle_id != id {
            return Err("invalid item response");
        }
        let valid = match code {
            "SMALL_POTION" => {
                matches!((u.healed_amount,u.current_hp,u.max_hp),(Some(h),Some(hp),Some(max)) if h>0&&max>0&&hp<=max&&h<=hp)
            }
            "BOND_BERRY" => matches!((u.bond_before,u.bond_after),(Some(b),Some(a)) if a>b),
            "CAPTURE_CHARM" => {
                u.armed == Some(true)
                    && u.bonus
                        .is_some_and(|b| b.is_finite() && b > 0.0 && b <= 1.0)
            }
            _ => false,
        };
        if !valid {
            return Err("invalid item result");
        }
        Ok(u)
    }
}
#[cfg(test)]
mod tests;
