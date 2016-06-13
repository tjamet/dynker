import sys
import argparse
import importlib
import glob
import os


def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='subparser help')
    known_modules = ['__init__', 'cmd']
    parsers = {}
    def display_help(args):
        if not args.command:
            parser.print_help()
            exit(1)
        if args.command in parsers:
            parsers[args.command].print_help()
            exit(1)
        else:
            raise ValueError("Unknown command %s" % args.command)
    def display_commands(args):
        for cmd in parsers:
            sys.stdout.write(cmd)
            sys.stdout.write("\n")
    for p in sys.modules['dynker'].__path__:
        for ext in '.py', '.pyc':
            for f in glob.glob(os.path.join(p,'*%s' % ext)):
                name = os.path.splitext(
                    os.path.basename(f)
                )[0]
                if name in known_modules:
                    continue
                module = importlib.import_module('dynker.%s' % name)
                if hasattr(module, 'main'):
                    command_name = getattr(module, 'COMMAND_NAME', name)
                    module_help = getattr(module.main, '__doc__', command_name)
                    subparser = subparsers.add_parser(command_name, help=module_help)
                    subparser.set_defaults(func=module.main)
                    parsers[command_name] = subparser
                    known_modules.append(command_name)
                    if hasattr(module, 'add_options'):
                        module.add_options(subparser)

    subparser = subparsers.add_parser('help', help='show this help message and exit')
    subparser.add_argument('command', nargs='?', help='the command to provide help on')
    subparser.set_defaults(func=display_help)

    subparser = subparsers.add_parser('list', help='list available commands and exit')
    subparser.set_defaults(func=display_commands)

    args = parser.parse_args(argv[1:])
    args.func(args=args)

if __name__=='__main__' :
    import os
    dynkerPath = os.path.dirname(os.path.dirname(__file__))
    sys.path.append(dynkerPath)
    main(name='dynker.__main__')
