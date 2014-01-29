import mock
import unittest
import structlog
import teeth_overlord.service


class EventLogger(unittest.TestCase):
	
	def test_format_event_basic(self):	
		structlog.configure(processors=[teeth_overlord.service._format_event])
		log = structlog.wrap_logger(structlog.ReturnLogger())
		logged_msg = log.msg("hello {word}", word='world', more_than_a_string=[1, 2, 3])
		self.assertEquals(logged_msg, "hello world")