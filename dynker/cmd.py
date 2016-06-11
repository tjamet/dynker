import sys

def main(argv=sys.argv, name=__name__) :
    if len(argv) < 2 :
        sys.stderr.write("Usage: %s <action>\n"%argv[0])
        exit(0)
    from . import alias
    action = argv.pop(1)
    action = alias.get(action,action)
    module = name.rsplit('.')[:-1]+[action]
    module = '.'.join(module)
    __import__(module)
    sys.modules[module].main(argv)

if __name__=='__main__' :
    import os
    dynkerPath = os.path.dirname(os.path.dirname(__file__))
    sys.path.append(dynkerPath)
    main(name='dynker.__main__')
