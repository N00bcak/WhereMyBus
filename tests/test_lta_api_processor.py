from src.setup_constants import sg_timezone, bus_types, bus_load
import src.lta_api_processor as test_subject
import unittest
import datetime

class TestParsing(unittest.TestCase):
    # Unit test the parser.
    def test_parse_arrival_data(self):
        dummy = {
            "Services": [
                {
                    "ServiceNo": "1",
                    "NextBus": {
                        "EstimatedArrival": datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone) + datetime.timedelta(seconds = 65)),
                        "Type": "SD",
                        "Load": "SEA"
                    }, 
                    "NextBus2": {
                        "EstimatedArrival": datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone) + datetime.timedelta(seconds = 125)),
                        "Type": "DD",
                        "Load": "SDA"
                    },
                    "NextBus3": {
                        "EstimatedArrival": datetime.datetime.isoformat(datetime.datetime.now(tz = sg_timezone) + datetime.timedelta(seconds = 185)),
                        "Type": "BD",
                        "Load": "LSD"
                    }
                }
            ]
        }
        self.assertEqual(test_subject.parse_arrival_data(dummy), f"<b>Bus No. 1</b>\n{bus_types['SD']} in 1 min {bus_load['SEA']}\n{bus_types['DD']} in 2 min {bus_load['SDA']}\n{bus_types['BD']} in 3 min {bus_load['LSD']}\n\n")

class TestComputations(unittest.TestCase):
    # Basic unit test for auxiliary computations done.
    def test_bus_arrival_is_int(self):
        self.assertIsInstance(test_subject.bus_est_arrival_min(datetime.datetime.now(tz = sg_timezone)), int)