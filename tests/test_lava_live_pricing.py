"""Merchant-only read freshness and currency policy; no real provider or database."""
import asyncio
import unittest
from unittest.mock import patch

from app.services.lava import events
from app.services.lava.client import LavaError
from app.services.lava.config import LavaConfigError, config_from_dict
from tests.lava_fakes import FakeLava, make_runtime


class LavaCurrencyPolicyTests(unittest.TestCase):
    def test_legacy_configuration_keeps_both_and_its_old_default(self):
        for currency in ('USD','RUB'):
            config=config_from_dict({'currency':currency})
            self.assertEqual(config.currency,currency)
            self.assertEqual(config.enabled_currencies,('USD','RUB'))

    def test_one_or_both_currencies_roundtrip_without_a_non_currency_default(self):
        for codes,default in [(['USD'],'USD'),(['RUB'],'RUB'),(['RUB','USD'],'RUB')]:
            config=config_from_dict({'currency':default,'enabled_currencies':codes})
            self.assertEqual(set(config.enabled_currencies),set(codes))
            self.assertEqual(config_from_dict(config.to_json()),config)

    def test_invalid_empty_duplicate_or_excluded_default_is_refused(self):
        for codes in ([],['EUR'],['USD','USD'],['RUB'],None,'USD'):
            with self.subTest(codes=codes),self.assertRaises(LavaConfigError):
                config_from_dict({'currency':'USD','enabled_currencies':codes})


class LavaCatalogCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_prices_refresh_after_expiry_without_a_settings_save(self):
        fake=FakeLava();runtime=make_runtime(None,fake)
        with patch.object(events,'monotonic',return_value=100):
            first=await runtime.products()
        fake.prices['MONTHLY']='12.00';fake.rub_prices={'MONTHLY':'649.00'}
        with patch.object(events,'monotonic',return_value=159):
            cached=await runtime.products()
        self.assertIs(first,cached)
        self.assertEqual(fake.calls,[('GET','/api/v2/products')])
        with patch.object(events,'monotonic',return_value=160):
            fresh=await runtime.products()
        offer=fresh[0].offers[0]
        self.assertEqual(str(offer.price_for('USD','MONTHLY').amount),'12.00')
        self.assertEqual(str(offer.price_for('RUB','MONTHLY').amount),'649.00')
        self.assertEqual(fake.calls,[('GET','/api/v2/products')]*2)

    async def test_concurrent_reads_share_one_task_and_one_cancelled_waiter_is_isolated(self):
        entered=asyncio.Event();release=asyncio.Event();calls=[]
        class Client:
            async def list_products(self):
                calls.append('GET');entered.set();await release.wait();return []
        runtime=make_runtime(None,FakeLava());runtime.client_factory=Client
        tasks=[asyncio.create_task(runtime.products()) for _ in range(5)]
        await entered.wait();tasks[0].cancel()
        with self.assertRaises(asyncio.CancelledError):await tasks[0]
        release.set()
        self.assertEqual(await asyncio.gather(*tasks[1:]),[()]*4)
        self.assertEqual(calls,['GET'])
        self.assertNotIn('catalog_task',runtime._state)

    async def test_failed_refresh_does_not_reuse_an_expired_price_and_recovers_after_backoff(self):
        fake=FakeLava();runtime=make_runtime(None,fake)
        with patch.object(events,'monotonic',return_value=100):await runtime.products()
        fake.unavailable=True
        with patch.object(events,'monotonic',return_value=160):
            with self.assertRaises(LavaError):await runtime.products()
        count=len(fake.calls);fake.unavailable=False
        with patch.object(events,'monotonic',return_value=164):
            with self.assertRaises(LavaError):await runtime.products()
        self.assertEqual(len(fake.calls),count)
        with patch.object(events,'monotonic',return_value=165):await runtime.products()
        self.assertEqual(len(fake.calls),count+1)

    async def test_whole_lookup_has_a_deadline_and_releases_its_task(self):
        cancelled=asyncio.Event()
        class Client:
            async def list_products(self):
                try:await asyncio.Event().wait()
                finally:cancelled.set()
        runtime=make_runtime(None,FakeLava());runtime.client_factory=Client
        with patch.object(events,'CATALOG_TIMEOUT_SECONDS',.02):
            with self.assertRaises(LavaError):await asyncio.wait_for(runtime.products(),1)
        self.assertTrue(cancelled.is_set())
        self.assertNotIn('catalog_task',runtime._state)

    async def test_runtime_catalogs_are_not_shared_between_merchants(self):
        one=FakeLava();two=FakeLava();two.prices['MONTHLY']='15.00'
        a,b=await asyncio.gather(make_runtime(None,one).products(),make_runtime(None,two).products())
        self.assertEqual(str(a[0].offers[0].price_for('USD','MONTHLY').amount),'10.00')
        self.assertEqual(str(b[0].offers[0].price_for('USD','MONTHLY').amount),'15.00')
