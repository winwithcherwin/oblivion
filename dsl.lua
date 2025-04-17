function step(func_name)
    return function(config)
        config = config or {}

        return {
            func = func_name,
            args = config.args or nil,
            register = config.register or nil,
	    enabled = config.enabled,
            name = config.name,
        }
    end
end

var = function(name)
  return function() return _G[name] end
end

function pipeline(steps)
    local formatted = {}
    for _, s in ipairs(steps) do
        local result = type(s) == "function" and s() or s
        print("→ Added step", result.func)
        table.insert(formatted, result)
    end
    execute_pipeline(formatted)
end

