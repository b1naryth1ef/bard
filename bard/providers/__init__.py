

def load_provider(bard, obj, config):
    return obj.get(config['name'])(bard, config)
