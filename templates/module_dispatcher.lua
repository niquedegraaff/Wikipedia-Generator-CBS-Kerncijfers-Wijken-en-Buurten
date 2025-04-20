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

    local jaar = mw.text.trim(jaar_arg)
    local regio = mw.text.trim(regio_arg)
    local stat_alias = mw.text.trim(stat_arg)

    if stat_alias == 'Ref' then
        if jaar == '' then
            return '<span class="error">Fout: Jaar parameter is vereist voor stat=Ref.</span>'
        end
        local data_module, err = get_data_module(jaar)
        if not data_module then
            return '<span class="error">' .. (err or 'Laden data module mislukt voor Ref.') .. '</span>'
        end
        local ds_id = data_module.dataset_id or 'ONBEKEND'
        local d_year = data_module.data_year or jaar
        local ref_name = 'CBS_KWB_' .. d_year
        local ref_url = 'https://opendata.cbs.nl/statline/#/CBS/nl/dataset/' .. ds_id .. '/table?dl=40544'
        local ref_titel = 'Kerncijfers Wijken en Buurten ' .. d_year
        local ref_uitgever = 'CBS'

        -- Bouw de {{Citeer web}} aanroep binnen de <ref> tag
        -- Gebruik mw.text.tag voor correcte <ref> generatie
        local cite_web_args = {
            ['url'] = ref_url,
            ['titel'] = ref_titel,
            ['uitgever'] = ref_uitgever,
        }
        -- Roep het Citeer web sjabloon aan binnen Lua
        local citation_wikitext = frame:expandTemplate{ title = 'Citeer web', args = cite_web_args }
        -- Genereer de <ref> tag
        local ref_tag = mw.text.tag{ name = 'ref', attrs = { name = ref_name }, content = citation_wikitext }

        return frame:preprocess(ref_tag)
    end

    -- === Code hieronder wordt alleen uitgevoerd als stat NIET 'Ref' is ===

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

    if output_value == nil then
        return nil
    else
        -- Geef alleen de waarde terug
        return tostring(output_value)
    end

end

return p