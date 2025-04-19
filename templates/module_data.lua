-- KWB Data Submodule %%YEAR%% (Dataset: %%DATASET_ID%%)
-- Automatisch gegenereerd: %%GENERATION_TIMESTAMP%%
-- Filtered: %%REGION_TYPES%% | Stripped stats (full keys): %%STATS_LIST_FULL%%
local p = {}

p.dataset_id = '%%DATASET_ID%%'
p.data_year = %%YEAR%%

-- Metadata alleen voor de opgenomen statistieken
p.metadata = {
%%METADATA_ENTRIES%%
}

-- Uitgeklede en gefilterde data (Gemeenten/Wijken only, opgegeven statistieken only)
p.data = {
%%DATA_ENTRIES%%
}

return p