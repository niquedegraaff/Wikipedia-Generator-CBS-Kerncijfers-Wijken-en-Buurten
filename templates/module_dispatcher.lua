-- Hoofdmodule (Dispatcher) voor CBS Kerncijfers Wijken en Buurten Data
local p = {}
local loaded_data = {} -- Cache

local function get_data_module(year)
    if not year then return nil, 'Jaar ontbreekt' end
    if not tonumber(year) or tonumber(year) < 2000 or tonumber(year) > 2100 then
        return nil, 'Ongeldig jaar: ' .. tostring(year)
    end
    if loaded_data[year] then return loaded_data[year] end

    local module_path = 'Module:%%MODULE_BASE_NAME%%/' .. year -- Pad naar submodule, met Module: prefix!
    local success, module_data = pcall(require, module_path)

    if success and module_data then
        loaded_data[year] = module_data
        return module_data
    else
        return nil, 'Kon data submodule niet laden: ' .. module_path
    end
end

function p.getStat(frame)
    local args = frame.args
    local parent_args = frame:getParent().args

    local jaar_arg = args.jaar or parent_args.jaar or ''
    local regio_arg = args.regio or parent_args.regio or ''
    local stat_arg = args.stat or parent_args.stat or ''
    local show_bron_arg = args.bron or parent_args.bron or ''

    local jaar = mw.text.trim(jaar_arg)
    local regio = mw.text.trim(regio_arg)
    local stat_alias = mw.text.trim(stat_arg)
    local show_bron = mw.text.trim(show_bron_arg):lower()

    -- <<< Check lege regio/stat VOORDAT module geladen wordt >>>
    if regio == '' or stat_alias == '' then
         return nil -- Sjabloon toont default '-'
    end
    -- <<< EINDE Check >>>

    -- Valideer jaar nu pas (als het is opgegeven)
    if jaar == '' then
         return '<span class="error">Fout: Jaar ontbreekt.</span>' -- Fout als jaar echt leeg is
    end

    -- Laad de data voor het gevraagde jaar
    local data_module, err = get_data_module(jaar)
    if not data_module then
        return '<span class="error">' .. (err or 'Laden data module mislukt.') .. '</span>'
    end

    -- Alias Mapping
    local internal_stat_key = stat_alias
%%ALIAS_MAPPING_BLOCK%%

    local regionData = data_module.data and data_module.data[regio]
    if not regionData then
         if string.sub(regio, 1, 2) == 'GM' or string.sub(regio, 1, 2) == 'WK' then
              return '<span class="error">Fout: Regio \'' .. regio .. '\' (GM/WK) niet gevonden voor jaar ' .. jaar .. '.</span>'
         else
              return '<span class="error">Fout: Regio \'' .. regio .. '\' niet gevonden (alleen GM/WK types).</span>'
         end
    end

    local value = regionData[internal_stat_key]
    local output_value

    if value == nil then
        if data_module.metadata and data_module.metadata[internal_stat_key] then
            output_value = nil -- Sjabloon toont default
        else
            return '<span class="error">Fout: Onbekende stat \'' .. stat_alias .. '\'.</span>'
        end
    else
        output_value = value
    end

    -- Bronvermelding
    local bron_suffix = ''
    if show_bron == 'ja' or show_bron == 'yes' or show_bron == '1' then
         local ds_id = data_module.dataset_id or 'ONBEKEND'
         local d_year = data_module.data_year or jaar
         local cbs_link = 'https://opendata.cbs.nl/statline/#/CBS/nl/dataset/' .. ds_id .. '/table?dl=40544'
         bron_suffix = ' <small>([https://opendata.cbs.nl/ CBS], KWB ' .. d_year .. ')</small>'
    end

    if output_value == nil then
        return nil
    else
        return tostring(output_value) .. bron_suffix
    end
end

return p