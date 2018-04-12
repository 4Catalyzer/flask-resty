import blinker

# -----------------------------------------------------------------------------

signals = blinker.Namespace()

got_handled_integrity_error = signals.signal('got-handled-integrity-error')
