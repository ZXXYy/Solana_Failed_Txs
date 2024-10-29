import unittest
import asyncio

from deprecated.analyze.jupiter import get_token_name

class TestJupiter(unittest.TestCase):
    def test_get_token_name(self):
        token_name = asyncio.run(self.async_test_get_token_name())
        self.assertIsNotNone(token_name)

    async def async_test_get_token_name(self):
        # This is the async version of your test
        token_account_address = "CnYkDeQphTtHGdfJspWeiUJpHnjq1PD1fHnSuKrr8eVh"
        token_name = await get_token_name(token_account_address)
        return token_name


if __name__ == "__main__":
    unittest.main()