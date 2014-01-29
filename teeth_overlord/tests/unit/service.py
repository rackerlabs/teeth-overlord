import mock
import unittest
import structlog
import teeth_overlord.service


def _return_event_processor(logger, method, event):
    return event['event']


class EventLogger(unittest.TestCase):
    def test_format_event_basic(self):
        processors = [teeth_overlord.service._format_event,
                      _return_event_processor]
        structlog.configure(processors=processors)
        log = structlog.wrap_logger(structlog.ReturnLogger())
        logged_msg = log.msg("hello {word}", word='world')
        self.assertEquals(logged_msg, "hello world")

    def test_no_format_keys(self):
        """Check that we get an exception if you don't provide enough keys to
        format a log message requiring format
        """
        processors = [teeth_overlord.service._format_event,
                      _return_event_processor]
        structlog.configure(processors=processors)
        log = structlog.wrap_logger(structlog.ReturnLogger())
        self.assertRaises(KeyError, log.msg, "hello {word}")
