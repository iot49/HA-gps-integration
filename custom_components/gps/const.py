DOMAIN = "gps"

CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE    = "baudrate"
CONF_TOL         = "tolerance"
CONF_QUALITY     = "quality"

DEFAULT_BAUDRATE = 4800
DEFAULT_TOL      = 1e-3    # report updates only if change > TOL
DEFAULT_QUALITY  = 1       # minimum GPS quality signal