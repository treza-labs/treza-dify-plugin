from dify_plugin import DifyPluginEnv, Plugin

# Video renders can take several minutes, so a tool call may run for up to 10.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=600))

if __name__ == "__main__":
    plugin.run()
