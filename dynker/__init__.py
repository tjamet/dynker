import logging
def addCommonOptions(parser) :
    parser.add_option("-v","--verbose",
                      dest="verbose", action="store_true",
                      help="switches the debug mode")
def commonSetUp(options) :
    if options.verbose :
        logging.basicConfig(level=logging.DEBUG)
    else :
        logging.basicConfig(level=logging.INFO)

alias={
    "build" : "builder",
}
