function pipeline(name)
  return setmetatable({}, {
    __call = function(_, block)
      print("== Pipeline: " .. name .. " ==")
      if type(block) == "function" then
        block()
      end
    end
  })
end

function step(name)
  return setmetatable({}, {
    __call = function(_, block)
      print("-- Step: " .. name .. " --")
      if type(block) == "function" then
        block()
      end
    end
  })
end

