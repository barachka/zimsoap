#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Integration tests against zimbraAdmin SOAP webservice

It has to be tested against a zimbra server (see README.md)
"""

import unittest
import random

from zimsoap.client import *
from zimsoap.zobjects import *

import tests

TEST_CONF = tests.get_config()

class ZimbraAdminClientTests(unittest.TestCase):
    def setUp(self):
        self.TEST_SERVER = TEST_CONF['host']
        self.TEST_LOGIN = TEST_CONF['admin_login']
        self.TEST_PASSWORD = TEST_CONF['admin_password']
        self.TEST_ADMIN_PORT = TEST_CONF['admin_port']
        self.LAMBDA_USER = TEST_CONF['lambda_user']
        self.SERVER_NAME = TEST_CONF['server_name']

    def testLogin(self):
        zc = ZimbraAdminClient(self.TEST_SERVER, self.TEST_ADMIN_PORT)
        zc.login(self.TEST_LOGIN, self.TEST_PASSWORD)
        self.assertTrue(zc._session.is_logged_in())

    def testBadLoginFailure(self):
        with self.assertRaises(ZimbraSoapServerError) as cm:
            zc = ZimbraAdminClient(self.TEST_SERVER, 7071)
            zc.login('badlogin@zimbratest.example.com', self.TEST_PASSWORD)

        self.assertIn('authentication failed', cm.exception.msg)


    def testBadPasswordFailure(self):
        with self.assertRaises(ZimbraSoapServerError) as cm:
            zc = ZimbraAdminClient(self.TEST_SERVER, 7071)
            zc.login(self.TEST_LOGIN, 'badpassword')

        self.assertIn('authentication failed', cm.exception.msg)

    def testBadHostFailure(self):
        with self.assertRaises(urllib2.URLError) as cm:
            zc = ZimbraAdminClient('nonexistanthost.example.com', 7071)
            zc.login(self.TEST_LOGIN, self.TEST_PASSWORD)

    def testBadPortFailure(self):
        with self.assertRaises(urllib2.URLError) as cm:
            zc = ZimbraAdminClient(self.TEST_SERVER, 9999)
            zc.login(self.TEST_LOGIN, self.TEST_PASSWORD)


class ZimbraAdminClientRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Login/connection is done at class initialization to reduce tests time
        cls.zc = ZimbraAdminClient(TEST_CONF['host'], TEST_CONF['admin_port'])
        cls.zc.login(TEST_CONF['admin_login'], TEST_CONF['admin_password'])


    def setUp(self):
        # self.zc = ZimbraAdminClient('zimbratest.example.com', 7071)
        # self.zc.login('admin@zimbratest.example.com', 'admintest')

        self.EXISTANT_DOMAIN = TEST_CONF['domain_1']
        self.EXISTANT_MBOX_ID = "d78fd9c9-f000-440b-bce6-ea938d40fa2d"
        # Should not exist before the tests
        self.TEST_DL_NAME = 'unittest-test-list-1@%s' % self.EXISTANT_DOMAIN

    def tearDown(self):
        # Try to delete a relief test distribution list (if any)
        try:
            resp = self.zc.request('GetDistributionList', {
                    'dl': {'by': 'name', '_content': self.TEST_DL_NAME}
            })

            dl_id = resp['dl']['id']
            self.zc.request('DeleteDistributionList', {'id': dl_id})

        except ZimbraSoapServerError:
            pass

    def testGetAllAccountsReturnsSomething(self):
        resp = self.zc.request('GetAllAccounts')
        self.assertTrue(resp.has_key('account'), list)
        self.assertIsInstance(resp['account'], list)

    def testGetAlllCalendarResourcesReturnsSomething(self):
        resp = self.zc.request_list('GetAllCalendarResources')
        #self.assertTrue(resp.has_key('calresource'), list)
        self.assertIsInstance(resp, list)

    def testGetAllDomainsReturnsSomething(self):
        resp = self.zc.request('GetAllDomains')
        self.assertTrue(resp.has_key('domain'), list)
        self.assertIsInstance(resp['domain'], list)

    def testGetDomainReturnsDomain(self):
        resp = self.zc.request('GetDomain', {'domain' : {
                    'by': 'name',
                    '_content': self.EXISTANT_DOMAIN
        }})
        self.assertIsInstance(resp, dict)
        self.assertTrue(resp.has_key('domain'))
        self.assertIsInstance(resp['domain'], dict)

    def testGetMailboxStatsReturnsSomething(self):
        resp = self.zc.request('GetMailboxStats')
        self.assertTrue(resp.has_key('stats'))
        self.assertIsInstance(resp['stats'], dict)

    def testCountAccountReturnsSomething(self):
        """Count accounts on the first of domains"""
        first_domain_name = self.zc.get_all_domains()[0].name

        resp = self.zc.request_list(
            'CountAccount',
            {'domain': {'by': 'name', '_content': self.EXISTANT_DOMAIN}}
        )
        first_cos = resp[0]
        self.assertTrue(first_cos.has_key('id'))

        # will fail if not convertible to int
        self.assertIsInstance(int(first_cos['_content']), int)

    def testGetMailboxRequest(self):
        try:
            EXISTANT_MBOX_ID = self.testGetAllMailboxes()[0]['accountId']
        except Exception as e:
            raise e('failed in self.testGetAllMailboxes()')

        resp = self.zc.request('GetMailbox', {'mbox': {'id': EXISTANT_MBOX_ID}})
        self.assertIsInstance(resp['mbox'], dict)
        self.assertTrue(resp['mbox'].has_key('mbxid'))


    def testGetAllMailboxes(self):
        resp = self.zc.request('GetAllMailboxes')
        mailboxes = resp['mbox']
        self.assertIsInstance(resp['mbox'], list)
        return mailboxes

    def testCreateGetDeleteDistributionList(self):
        """ As Getting and deleting a list requires it to exist
        a list to exist, we group the 3 tests together.
        """

        def createDistributionList(name):
            resp = self.zc.request('CreateDistributionList', {'name': name})

            self.assertIsInstance(resp['dl'], dict)

        def getDistributionList(name):
            resp = self.zc.request('GetDistributionList',
                                   {'dl': {'by': 'name', '_content': name}})

            self.assertIsInstance(resp['dl'], dict)
            self.assertIsInstance(resp['dl']['id'], unicode)
            return resp['dl']['id']

        def deleteDistributionList(dl_id):
            resp = self.zc.request('DeleteDistributionList', {'id': dl_id})

        # Should not exist
        with self.assertRaises(ZimbraSoapServerError) as cm:
            getDistributionList(self.TEST_DL_NAME)

        createDistributionList(self.TEST_DL_NAME)

        # It should now exist
        list_id = getDistributionList(self.TEST_DL_NAME)

        deleteDistributionList(list_id)

        # Should no longer exists
        with self.assertRaises(ZimbraSoapServerError) as cm:
            getDistributionList(self.TEST_DL_NAME)


    def testCheckDomainMXRecord(self):

        domain = {'by': 'name', '_content': self.EXISTANT_DOMAIN}
        try:
            resp = self.zc.request('CheckDomainMXRecord', {'domain': domain})

        except ZimbraSoapServerError as sf:
            if not 'NameNotFoundException' in str(sf):
                # Accept for the moment this exception as it's kind a response
                # from server.
                raise

    def testGetAccount(self):
        account = {'by': 'name', '_content': TEST_CONF['lambda_user']}
        resp = self.zc.request('GetAccount', {'account': account})
        self.assertIsInstance(resp['account'], dict)

    def testGetAccountInfo(self):
        account = {'by': 'name', '_content': TEST_CONF['lambda_user']}
        resp = self.zc.request('GetAccountInfo', {'account': account})
        self.assertIsInstance(resp['cos']['id'], (str, unicode))


class PythonicAdminAPITests(unittest.TestCase):
    """ Tests the pythonic API, the one that should be accessed by someone using
    the library, zimbraAdmin features.
    """

    @classmethod
    def setUpClass(cls):
        # Login/connection is done at class initialization to reduce tests time
        cls.zc = ZimbraAdminClient(TEST_CONF['host'],
                                   TEST_CONF['admin_port'])
        cls.zc.login(TEST_CONF['admin_login'], TEST_CONF['admin_password'])

    def setUp(self):
        # self.zc = ZimbraAdminClient('zimbratest.example.com', 7071)
        # self.zc.login('admin@zimbratest.example.com', 'admintest')
        self.HOST = TEST_CONF['host']
        self.ADMIN_PASSWORD = TEST_CONF['admin_password']
        self.ADMIN_PORT = TEST_CONF['admin_port']
        self.ADMIN_LOGIN = TEST_CONF['admin_login']
        self.LAMBDA_USER = TEST_CONF['lambda_user']
        self.DOMAIN1 = TEST_CONF['domain_1']
        self.DOMAIN2 = TEST_CONF['domain_2']
        self.SERVER_NAME = TEST_CONF['server_name']

        self.EXISTANT_MBOX_ID = "d78fd9c9-f000-440b-bce6-ea938d40fa2d"
        # Should not exist before the tests
        self.TEST_DL_NAME = 'unittest-test-list-1@%s' % self.DOMAIN1

    def tearDown(self):
        try:
            self.zc.delete_distribution_list(
                DistributionList(name=self.TEST_DL_NAME))
        except (ZimbraSoapServerError, KeyError):
            pass

    def test_get_all_domains(self):
        doms = self.zc.get_all_domains()
        self.assertIsInstance(doms, list)
        self.assertIsInstance(doms[0], Domain)

        # Look for client1.unbound.example.com
        found = False
        for i in doms:
            if i.name == self.DOMAIN1:
                found = True

        self.assertTrue(found)

    def test_get_domain(self):
        dom = self.zc.get_domain(Domain(name=self.DOMAIN1))
        self.assertIsInstance(dom, Domain)
        self.assertEqual(dom.name, self.DOMAIN1)

    def test_modify_domain(self):
        rand_str = random.randint(0,10**9)

        dom = self.zc.get_domain(Domain(name=self.DOMAIN1))
        a = {'zimbraAutoProvNotificationBody': rand_str}
        self.zc.modify_domain(dom, a)

        dom = self.zc.get_domain(Domain(name=self.DOMAIN1))
        self.assertEqual(dom['zimbraAutoProvNotificationBody'], rand_str)

    def test_get_all_accounts(self):
        accounts = self.zc.get_all_accounts()
        self.assertIsInstance(accounts[0], Account)
        self.assertEqual(len(accounts), 16)

    def test_get_all_accounts_by_single_server(self):
        test_server = Server(name=self.SERVER_NAME)
        accounts = self.zc.get_all_accounts(server=test_server)
        self.assertIsInstance(accounts[0], Account)
        self.assertEqual(len(accounts), 16)

    def test_get_all_accounts_by_single_domain(self):
        test_domain = Domain(name=self.DOMAIN2)
        accounts = self.zc.get_all_accounts(domain=test_domain)
        self.assertIsInstance(accounts[0], Account)
        self.assertEqual(len(accounts), 5)

    def test_get_all_accounts_by_single_domain_and_server(self):
        test_domain = Domain(name=self.DOMAIN2)
        test_server = Server(name=self.SERVER_NAME)
        accounts = self.zc.get_all_accounts(domain=test_domain,
                                            server=test_server)
        self.assertIsInstance(accounts[0], Account)
        self.assertEqual(len(accounts), 5)

    def test_get_all_accounts_exclusion_filters(self):
        # The self.DOMAIN1 contains 5 user accounts, 1 system and 1 admin
        test_domain = Domain(name=self.DOMAIN1)

        accounts = self.zc.get_all_accounts(
            domain=test_domain,
            include_system_accounts=True, include_admin_accounts=True)
        self.assertEqual(len(accounts), 7)

        accounts_no_admin = self.zc.get_all_accounts(
            domain=test_domain,
            include_system_accounts=True, include_admin_accounts=False)
        self.assertEqual(len(accounts_no_admin), 6)

        accounts_no_system = self.zc.get_all_accounts(
            domain=test_domain,
            include_system_accounts=False, include_admin_accounts=True)
        self.assertEqual(len(accounts_no_system), 6)

        accounts_no_admin_no_system = self.zc.get_all_accounts(
            domain=test_domain,
            include_admin_accounts=False, include_system_accounts=False)
        self.assertEqual(len(accounts_no_admin_no_system), 5)

    def test_get_all_calendar_resources(self):
        resources = self.zc.get_all_calendar_resources()
        self.assertIsInstance(resources[0], CalendarResource)
        self.assertEqual(len(resources), 2)

    def test_get_all_calendar_resources_by_single_server(self):
        test_server = Server(name=self.SERVER_NAME)
        resources = self.zc.get_all_calendar_resources(server=test_server)
        self.assertIsInstance(resources[0], CalendarResource)
        self.assertEqual(len(resources), 2)

    def test_get_all_calendar_resources_by_single_domain(self):
        test_domain = Domain(name=self.DOMAIN2)
        resources = self.zc.get_all_calendar_resources(domain=test_domain)
        self.assertEqual(len(resources), 1)

    def test_get_calendar_resource(self):
        calendar_resource = self.zc.get_calendar_resource(
            CalendarResource(name=TEST_CONF['calres1']))
        self.assertIsInstance(calendar_resource, CalendarResource)
        self.assertEqual(calendar_resource.name, TEST_CONF['calres1'])

        # Now grab it by ID
        calendar_resource_by_id = self.zc.get_calendar_resource(
            CalendarResource(id=calendar_resource.id))
        self.assertIsInstance(calendar_resource_by_id, CalendarResource)
        self.assertEqual(calendar_resource_by_id.name, TEST_CONF['calres1'])
        self.assertEqual(calendar_resource_by_id.id, calendar_resource.id)


    def test_create_get_update_delete_calendar_resource(self):
        name = 'test-{}@zimbratest.example.com'.format(
            random.randint(0,10**9))
        res_req = CalendarResource(name=name)

        with self.assertRaises(ZimbraSoapServerError) as cm:
            self.zc.get_calendar_resource(res_req)

        # CREATE
        res = self.zc.create_calendar_resource(name, attrs={
            'displayName'     : 'test display name',
            'zimbraCalResType': CalendarResource.EQUIPMENT_TYPE
        })

        self.assertIsInstance(res, CalendarResource)
        self.assertEqual(res.name, name)

        # GET
        res_got = self.zc.get_calendar_resource(res_req)
        self.assertIsInstance(res_got, CalendarResource)
        self.assertEqual(res.name, name)

        # UPDATE
        random_name_1 =  'test-{}'.format(random.randint(0,10**9))
        self.zc.modify_calendar_resource(res_got, {'displayName': random_name_1})

        res_got = self.zc.get_calendar_resource(res_req)
        self.assertEqual(res_got['displayName'], random_name_1)

        # DELETE
        self.zc.delete_calendar_resource(res_got)

        with self.assertRaises(ZimbraSoapServerError) as cm:
            self.zc.get_calendar_resource(res)

    def test_create_get_update_delete_account(self):
        name = 'test-{}@zimbratest.example.com'.format(
            random.randint(0,10**9))
        password = 'pass124'
        ac_req = Account(name=name)

        with self.assertRaises(ZimbraSoapServerError) as cm:
            self.zc.get_account(ac_req)

        # CREATE
        ac = self.zc.create_account(name, password)

        self.assertIsInstance(ac, Account)
        self.assertEqual(ac.name, name)

        # GET
        ac_got = self.zc.get_account(ac_req)
        self.assertIsInstance(ac_got, Account)
        self.assertEqual(ac_got.name, name)

        # UPDATE
        random_name_1 =  'test-{}'.format(random.randint(0,10**9))
        self.zc.modify_account(ac_got, {'displayName': random_name_1})

        ac_got = self.zc.get_account(ac_req)
        self.assertEqual(ac_got['displayName'], random_name_1)

        # DELETE
        self.zc.delete_account(ac_got)

        with self.assertRaises(ZimbraSoapServerError) as cm:
            self.zc.get_account(ac)

    def test_create_delete_account_alias(self):

        # prepare account

        ac_name = 'test-{}@zimbratest.example.com'.format(
            random.randint(0,10**9))
        ac = self.zc.create_account(ac_name, 'pass1234')

        alias_name = 'test-{}@zimbratest.example.com'.format(
            random.randint(0,10**9))

        # CREATE
        retval = self.zc.add_account_alias(Account(name=ac_name), alias_name)

        self.assertEqual(retval, None)

        # GET
        ac_got = self.zc.get_account(Account(name=ac_name))
        self.assertIn(alias_name, ac_got['mail'])

        # DELETE
        self.zc.remove_account_alias(ac, alias_name)

        # GET
        ac_got = self.zc.get_account(Account(name=ac_name))
        self.assertNotIn(alias_name, ac_got['mail'])

        self.zc.delete_account(ac)


    def test_get_mailbox_stats(self):
        stats = self.zc.get_mailbox_stats()
        self.assertIsInstance(stats, dict)
        self.assertIsInstance(stats['numMboxes'], int)
        self.assertIsInstance(stats['totalSize'], int)

    def test_count_account(self):
        d = Domain(name=self.DOMAIN1)

        # ex return: list: ((<ClassOfService object>, <int>), ...)
        cos_counts = self.zc.count_account(d)

        self.assertIsInstance(cos_counts, list)
        self.assertIsInstance(cos_counts[0], tuple)
        self.assertIsInstance(cos_counts[0][0], ClassOfService)
        self.assertIsInstance(cos_counts[0][1], int)

    def test_get_all_mailboxes(self):
        mboxes = self.zc.get_all_mailboxes()
        self.assertIsInstance(mboxes, list)
        self.assertIsInstance(mboxes[0], Mailbox)

    def test_account_mailbox(self):
        # First, fetch an existing account_id
        first_account_id = self.zc.get_all_mailboxes()[0].accountId

        mbox = self.zc.get_account_mailbox(first_account_id)
        self.assertTrue(hasattr(mbox, 'mbxid'))
        self.assertTrue(hasattr(mbox, 's')) # size


    def test_create_get_modify_delete_distribution_list(self):
        name = self.TEST_DL_NAME
        dl_req = DistributionList(name=name)

        with self.assertRaises(ZimbraSoapServerError) as cm:
            print self.zc.get_distribution_list(dl_req)

        dl = self.zc.create_distribution_list(name)
        self.assertIsInstance(dl, DistributionList)
        self.assertEqual(dl.name, name)

        dl_list = self.zc.get_all_distribution_lists()
        self.assertIsInstance(dl_list[1], DistributionList)

        self.zc.add_distribution_list_member(
            dl,['someone@example.com', 'another@example.com'])

        dl_membered = self.zc.get_distribution_list(dl_req)
        self.assertEqual(
            set(dl_membered.members),
            set(['someone@example.com', 'another@example.com']))

        self.zc.remove_distribution_list_member(
            dl,['someone@example.com'])
        dl_unmembered = self.zc.get_distribution_list(dl_req)
        self.assertEqual(dl_unmembered.members, ['another@example.com'])

        rand = 'list-{}'.format(random.randint(0,10**9))
        self.zc.modify_distribution_list(dl, {'displayName': rand})
        dl_modified = self.zc.get_distribution_list(dl_req)
        self.assertEqual(dl_modified.property('displayName'), rand)

        dl_got = self.zc.get_distribution_list(dl_req)
        self.assertIsInstance(dl_got, DistributionList)
        self.assertEqual(dl_got, dl_list[1])

        self.zc.delete_distribution_list(dl_got)

        with self.assertRaises(ZimbraSoapServerError) as cm:
            self.zc.get_distribution_list(dl)

    def test_delete_distribution_list_by_name(self):
        name = self.TEST_DL_NAME
        dl_req = DistributionList(name=name)
        dl_full = self.zc.create_distribution_list(name)
        self.zc.delete_distribution_list(dl_req)

        # List with such a name does not exist
        with self.assertRaises(ZimbraSoapServerError) as cm:
            self.zc.get_distribution_list(dl_req)

        # List with such an ID does not exist
        with self.assertRaises(ZimbraSoapServerError) as cm:
            self.zc.get_distribution_list(dl_full)

    def test_get_account(self):
        account = self.zc.get_account(Account(name=self.LAMBDA_USER))
        self.assertIsInstance(account, Account)
        self.assertEqual(account.name, self.LAMBDA_USER)

        # Now grab it by ID
        account_by_id = self.zc.get_account(Account(id=account.id))
        self.assertIsInstance(account_by_id, Account)
        self.assertEqual(account_by_id.name, self.LAMBDA_USER)
        self.assertEqual(account_by_id.id, account.id)

    def test_get_account_cos(self):
        cos = self.zc.get_account_cos(Account(name=self.LAMBDA_USER))
        self.assertIsInstance(cos, COS)
        self.assertEqual(cos.name, 'default')
        self.assertRegexpMatches(cos.id, r'[\w\-]{36}')

    def test_mk_auth_token_succeeds(self):
        user = Account(name='admin@{0}'.format(self.DOMAIN1))
        tk = self.zc.mk_auth_token(user, 0)
        self.assertIsInstance(tk, str)

    def test_mk_auth_token_fails_if_no_key(self):
        user = Account(name='admin@{0}'.format(self.DOMAIN2))

        with self.assertRaises(DomainHasNoPreAuthKey) as cm:
            self.zc.mk_auth_token(user, 0)

    def test_admin_get_logged_in_by(self):
        new_zc = ZimbraAdminClient(self.HOST, self.ADMIN_PORT)
        new_zc.get_logged_in_by(self.ADMIN_LOGIN, self.zc)
        self.assertTrue(new_zc._session.is_logged_in())
        self.assertTrue(new_zc.is_session_valid())

    def test_deprecated_admin_delegate_auth(self):
        # Cannot assertWarns before py3.2
        zc_account = self.zc.delegate_auth(Account(name=self.LAMBDA_USER))
        self.assertTrue(zc_account._session.is_logged_in())
        self.assertTrue(zc_account.is_session_valid())

    def test_admin_get_account_authToken1(self):
        """ From an existing account """
        authToken, lifetime = self.zc.get_account_authToken(
            account=Account(name=self.LAMBDA_USER)
        )
        new_zc = ZimbraAccountClient(self.HOST)
        new_zc.login_with_authToken(authToken, lifetime)
        self.assertTrue(new_zc._session.is_logged_in())
        self.assertTrue(new_zc.is_session_valid())

    def test_admin_get_account_authToken2(self):
        """ From an account name """
        authToken, lifetime = self.zc.get_account_authToken(
            account_name=self.LAMBDA_USER
        )
        new_zc = ZimbraAccountClient(self.HOST)
        new_zc.login_with_authToken(authToken, lifetime)
        self.assertTrue(new_zc._session.is_logged_in())
        self.assertTrue(new_zc.is_session_valid())


class ZimbraAPISessionTests(unittest.TestCase):
    def setUp(self):
        self.HOST = TEST_CONF['host']
        self.ADMIN_PORT = TEST_CONF['admin_port']
        self.ADMIN_LOGIN = TEST_CONF['admin_login']
        self.ADMIN_PASSWORD = TEST_CONF['admin_password']

        self.cli = ZimbraAdminClient(self.HOST, self.ADMIN_PORT)
        self.session = ZimbraAPISession(self.cli)

    def testInit(self):
        self.session = ZimbraAPISession(self.cli)
        self.assertFalse(self.session.is_logged_in())

    def testSuccessfullLogin(self):
        self.session.login(self.ADMIN_LOGIN, self.ADMIN_PASSWORD)

        self.assertTrue(self.session.is_logged_in())

    def testGoodSessionValidates(self):
        self.session.login(self.ADMIN_LOGIN, self.ADMIN_PASSWORD)
        self.assertTrue(self.session.is_session_valid())

    def testBadSessionFails(self):
        self.session.login(self.ADMIN_LOGIN, self.ADMIN_PASSWORD)
        self.session.authToken = '42'
        self.assertFalse(self.session.is_session_valid())
