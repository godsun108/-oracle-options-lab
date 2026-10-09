import io
import unittest
import urllib.error
from research.paco_tradier_auth_diagnostic import probe

class Resp(io.BytesIO):
    status=200
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
def opener(req,timeout):
    assert req.get_method()=="GET"
    if "options/expirations" in req.full_url:
        raise urllib.error.HTTPError(req.full_url,401,"Unauthorized",{},None)
    return Resp(b"{}")
class AuthTests(unittest.TestCase):
    def test_distinguishes_endpoint_specific_401(self):
        result=probe("fixture-token",opener=opener)
        self.assertEqual(result["diagnosis"],"OPTIONS_ENDPOINT_REJECTS_TOKEN_WHILE_UNDERLYING_WORKS")
        self.assertNotIn("fixture-token",str(result))
        self.assertFalse(result["orders_enabled"])
    def test_requires_token(self):
        with self.assertRaises(ValueError):probe("")
if __name__=="__main__":unittest.main()
