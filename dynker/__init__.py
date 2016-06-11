import logging
def addCommonOptions(parser) :
    parser.add_option("-v","--verbose",
                      dest="verbose", action="count",
                      help="switches the debug mode -v sets info logging, -vv sets debug logging")
def commonSetUp(options) :
    if options.verbose>1 :
        logging.basicConfig(level=logging.DEBUG)
    elif options.verbose==1:
        logging.basicConfig(level=logging.INFO)
    else :
        logging.basicConfig(level=logging.WARNING)

alias={
    "build" : "builder",
}
