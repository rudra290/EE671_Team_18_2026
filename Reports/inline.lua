-- inline-links.lua
function Para(el)
  -- Check if paragraph consists of a single link to a .md file
  if #el.content == 1 and el.content[1].tag == "Link" then
    local link = el.content[1]
    local target = link.target

    if target:match("%.md$") or target:match("%.markdown$") then
      local f = io.open(target, "r")
      if f then
        local content = f:read("*a")
        f:close()
        -- Parse the referenced Markdown file and inject its blocks directly
        local doc = pandoc.read(content, "markdown")
        return doc.blocks
      else
        io.stderr:write("[WARNING] Could not find linked file: " .. target .. "\n")
      end
    end
  end
end
