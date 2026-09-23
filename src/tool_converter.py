def convert_all_tools(tools):
    # Langchain tools can be directly passed to bind_tools. 
    # We just return the list of tools as they are already @tool wrapped.
    return tools
