import logging
def addCommonOptions(parser) :
    try:
        add = parser.add_argument
    except AttributeError:
        add = parser.add_option
    add("-v","--verbose",
                      dest="verbose", action="count", default=0,
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
