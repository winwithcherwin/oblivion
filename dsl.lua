function step(func_name)
    return function(args)
        args = args or {}
        return {func = func_name, args = args}
    end
end

function pipeline(steps)
    local formatted_steps = {}
    for _, s in ipairs(steps) do
        if type(s) == "function" then
            table.insert(formatted_steps, s())
        else
            table.insert(formatted_steps, s)
        end
    end
    execute_pipeline(formatted_steps)
end

