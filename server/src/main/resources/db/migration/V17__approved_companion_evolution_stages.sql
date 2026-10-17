-- Approved concept stage names; existing species IDs, MOA names and saved progression remain unchanged.
INSERT INTO game.m_species_evolution(species_id,evolution_stage,name)
SELECT s.species_id,v.stage,v.name FROM game.m_species s JOIN (VALUES
('RUU',2,'GLIDE'),('RUU',3,'SKYFIN'),('RUU',4,'AERIAL'),('RUU',5,'ZENITH'),
('NOX',2,'VEIL'),('NOX',3,'PHANTOM'),('NOX',4,'OBSCURA'),('NOX',5,'ECLIPS')
) AS v(code,stage,name) ON s.code=v.code;
