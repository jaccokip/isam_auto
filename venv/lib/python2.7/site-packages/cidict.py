class cidict(dict):
    '''Case insensitive dictionary.
    '''
    
    def __init__(self, mapping=None, **kwargs):
        super(cidict, self).__init__()
        
        if mapping:
            # uses our update()
            self.update(mapping)
        if kwargs:
            self.update(kwargs)
    
    def __delitem__(self, key):
        super(cidict, self).__delitem__(key.lower())
    
    def __getitem__(self, key):
        return super(cidict, self).__getitem__(key.lower())
    
    def __setitem__(self, key, value):
        super(cidict, self).__setitem__(key.lower(), value)
    
    def __contains__(self, key):
        return super(cidict, self).__contains__(key.lower())
    
    has_key = __contains__
    
    def update(self, other):
        for key in other:
            # uses our __setitem__, no need to lower() here
            self[key] = other[key]
