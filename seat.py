import requests
from errbot import BotPlugin, botcmd
import datetime
import logging
import redis


class Seat(BotPlugin):
    """Seat API to errbot"""

    def activate(self):
        super(Seat, self).activate()
        self.logger = logging
        self.seat_headers = {
            'X-Token': self.config['SEAT_TOKEN'], 'Accept': 'application/json'}

        if self.config['CHECK_STRUCTURES']:
            self.start_poller(3600, self._poller_pos_check)
            self.start_poller(3600, self._poller_pos_clear_warnings)
        if self.config['CHECK_TRADES']:
            self.start_poller(900, self._poller_transactions_check)
        if self.config['CHECK_CONTRACTS']:
            self.start_poller(900, self._poller_contracts_check)
        if self.config['CHECK_INDUSTRY']:
            self.start_poller(900, self._poller_industry_check)
        if 'last_trade_id' not in self:
            self['last_trade_id'] = 1
        if 'last_contract_id' not in self:
            self['last_contract_id'] = 1
        if 'last_job_id' not in self:
            self['last_job_id'] = 1

        self.redis = redis.StrictRedis(host='localhost', port=6379, db=9)

    ####################################################################################################################
    # Configuration

    def get_configuration_template(self):
        return {
            'SEAT_TOKEN': '<seat_token>',
            'SEAT_URL': '<your_seat_url>',
            'FUEL_THRESHOLD': 24,
            'STRONT_THRESHOLD': 12,
            'CHECK_STRUCTURES': True,
            'CHECK_TRADES': True,
            'CHECK_CONTRACTS': True,
            'CHECK_INDUSTRY': True,
            'CORP_ID': '<corpid>',
            'REPORT_POS_CHAN': '<channel>',
            'REPORT_REINF_CHAN': '<channel>',
            'REPORT_TRADES_CHAN': '<channel>',
            'REPORT_INDUSTRY_CHAN': '<channel>',
            'REPORT_CONTRACTS_CHAN': '<channel>'
        }

    ####################################################################################################################
    # Helper
    def strfdelta(self, tdelta, fmt):
        d = {"days": tdelta.days}
        d["hours"], rem = divmod(tdelta.seconds, 3600)
        d["minutes"], d["seconds"] = divmod(rem, 60)
        return fmt.format(**d)

    ####################################################################################################################
    # ESI api Calls

    def get_or_set(self, key, value):
        if self.redis.get(key):
            return self.redis.get(key).decode('utf-8')
        self.redis.set(key, value)
        return self.redis.get(key).decode('utf-8')

    def get_pilot(self, id):
        try:
            r = requests.get(
                'https://esi.evetech.net/latest/characters/{}'.format(str(id)))
            r.raise_for_status()
            value = r.json()['name']
            return self.get_or_set(str(id), value)

        except requests.exceptions.RequestException as e:
            self.logger.info(
                'Got a connection reset error from esi interface: {}'.format(e))
            return 'unknown'

    def get_item(self, id):
        try:
            r = requests.get(
                'https://esi.evetech.net/latest/universe/types/{}'.format(str(id)))
            r.raise_for_status()
            value = r.json()['name']
            return self.get_or_set(str(id), value)

        except requests.exceptions.RequestException as e:
            self.logger.info(
                'Got a connection reset error from esi interface: {}'.format(e))
            return 'unknown'

    def get_corporation(self, id):
        try:
            r = requests.get(
                'https://esi.evetech.net/latest/corporations/{}'.format(str(id)))
            r.raise_for_status()
            value = r.json()['name']
            return self.get_or_set(str(id), value)

        except requests.exceptions.RequestException as e:
            self.logger.info(
                'Got a connection reset error from esi interface: {}'.format(e))
            return 'unknown'

    def get_alliance(self, id):
        try:
            r = requests.get(
                'https://esi.evetech.net/latest/alliances/{}'.format(str(id)))
            r.raise_for_status()
            value = r.json()['name']
            return self.get_or_set(str(id), value)

        except requests.exceptions.RequestException as e:
            self.logger.info(
                'Got a connection reset error from esi interface: {}'.format(e))
            return 'unknown'

    def get_station_name(self, id):
        try:
            r = requests.get(
                'https://esi.evetech.net/latest/universe/stations/{}'.format(str(id)))
            r.raise_for_status()
            value = r.json()['name']
            return self.get_or_set(str(id), value)

        except requests.exceptions.RequestException as e:
            self.logger.info(
                'Got a connection reset error from esi interface: {}'.format(e))
            return 'unknown Station'

    ####################################################################################################################
    # Seat Api Calls

    def api_call(self, url):
        try:
            r = requests.get(url, headers=self.seat_headers)
            if r.status_code == requests.codes.ok:
                return r.json()
            else:
                self.logger.error(
                    "Problem with status code for %s got %s" % (url, r.status_code))
        except requests.exceptions.ConnectionError as e:
            self.logger.error('Got a connection reset error:' + e)

    def get_corps(self):
        url = self.config['SEAT_URL'] + "/corporation/all"
        return self.api_call(url)

    def get_starbases(self, corpid):
        url = self.config['SEAT_URL'] + "/corporation/starbases/" + str(corpid)
        return self.api_call(url)

    def get_pocos(self, corpid):
        url = self.config['SEAT_URL'] + "/corporation/pocos/" + str(corpid)
        return self.api_call(url)

    def get_pos_contents(self, corpid, posid):
        url = self.config['SEAT_URL'] + \
            "/corporation/starbases/" + str(corpid) + "/" + str(posid)
        return self.api_call(url)

    def get_transactions(self, corpid):
        url = self.config['SEAT_URL'] + \
            "/corporation/wallet-transactions/" + str(corpid)
        # get 3 last pages for buying sprees
        allItems = []
        totalPages = self.api_call(url)['meta']['last_page']
        startPage = totalPages-3 if not totalPages < 4 else 0
        for i in range(startPage, totalPages):
            items = self.api_call(url + '?page=' + str(i))['data']
            allItems += items
        return allItems

    def get_contracts(self, corpid):
        url = self.config['SEAT_URL'] + \
            "/corporation/contracts/" + str(corpid)
        allContracts = []
        totalPages = self.api_call(url)['meta']['last_page']
        startPage = totalPages-3 if not totalPages < 4 else 0
        for i in range(startPage, totalPages):
            contracts = self.api_call(url + '?page=' + str(i))['data']
            allContracts += contracts
        return allContracts

    def get_industry(self, corpid):
        url = self.config['SEAT_URL'] + \
            "/corporation/industry/" + str(corpid)
        allJobs = []
        totalPages = self.api_call(url)['meta']['last_page']
        startPage = totalPages-3 if not totalPages < 4 else 0
        for i in range(startPage, totalPages):
            jobs = self.api_call(url + '?page=' + str(i))['data']
            allJobs += jobs
        return allJobs

    ####################################################################################################################
    # Reporting states

    def set_warning(self, itemid, warn_type, enabled=True):
        """Sets warning states to given itemid"""
        itemid = str(itemid)
        if itemid not in self:
            self[itemid] = {}
        with self.mutable(itemid) as d:
            d[warn_type] = enabled

    def check_warning(self, itemid, warning):
        """Checks warning state for given itemid. If none present returns True"""
        itemid = str(itemid)
        if itemid in self:
            if warning in self[itemid]:
                return self[itemid][warning]
        else:
            return True

    ####################################################################################################################
    # Checks

    def check_fuel(self, starbase):
        if starbase['state'] == 1:
            return False
        fuel_left = starbase['fuelBlocks'] / starbase['baseFuelUsage']
        if int(fuel_left) <= self.config['FUEL_THRESHOLD']:
            return True
        else:
            return False

    def check_outdated(self, starbase):
        # last_updated does not change on reinforced or anchored/offline pos
        if starbase['state'] == 1 or starbase['state'] == 3:
            return False

        last_update = datetime.datetime.strptime(
            starbase['updated_at'], "%Y-%m-%d %H:%M:%S")
        if last_update < datetime.datetime.utcnow() - datetime.timedelta(hours=12):
            return True
        else:
            return False

    def check_stront(self, starbase):
        if starbase['state'] == 1 or starbase['state'] == 3:
            return False
        stront_left = starbase['strontium'] / starbase['baseStrontUsage']
        if int(stront_left) <= self.config['STRONT_THRESHOLD']:
            return True
        else:
            return False

    def check_reinforced(self, starbase):
        if starbase['state'] == 3:
            return True
        else:
            return False

    ####################################################################################################################
    # poller

    def _poller_transactions_check(self):
        lastTransactions = self.get_transactions(self.config['CORP_ID'])
        for transaction in lastTransactions:
            if self['last_trade_id'] < transaction['transaction_id']:
                self['last_trade_id'] = transaction['transaction_id']
                quantity = transaction['quantity']
                typeName = transaction['type']['typeName']
                action = "Sold" if transaction['is_buy'] == 0 else "Bought"
                price = '{:,.2f}'.format(transaction['unit_price'])
                priceTotal = '{:,.2f}'.format(
                    quantity*transaction['unit_price'])
                self.send(self.build_identifier(self.config['REPORT_TRADES_CHAN']),
                          ":moneybag: {} {}x {} at {}. Total: {}".format(
                              action, quantity, typeName, price, priceTotal))

    def _poller_contracts_check(self):
        contracts = self.get_contracts(self.config['CORP_ID'])
        for contract in contracts:
            if contract['detail']['type'] == 'courier':
                # cast some vars
                apiStatus = contract['detail']['status']
                contractID = contract['detail']['contract_id']
                reward = '{:,.2f}'.format(contract['detail']['reward'])
                collateral = '{:,.2f}'.format(
                    contract['detail']['collateral'])
                volume = contract['detail']['volume']
                source = self.get_station_name(
                    contract['detail']['start_location_id'])
                destination = self.get_station_name(
                    contract['detail']['end_location_id'])
                # check for updates
                selfStatus = self.get_or_set(contractID, apiStatus)
                if selfStatus != apiStatus:
                    self.send(self.build_identifier(self.config['REPORT_CONTRACTS_CHAN']),
                              ":airplane: Update: {} --> {} from {} to {}".format(
                                  source, destination, selfStatus, apiStatus))
                # check for new
                if self['last_contract_id'] < contract['contract_id']:
                    self['last_contract_id'] = contract['contract_id']
                    self.send(self.build_identifier(self.config['REPORT_CONTRACTS_CHAN']),
                              ":airplane: New: {} - -> {} | {} volume  {} reward  {} collateral".format(
                                  source, destination, volume, reward, collateral))

    def _poller_industry_check(self):
        jobs = self.get_industry(self.config['CORP_ID'])
        for job in jobs:
            # cast some vars
            jobID = job['job_id']
            installer = self.get_pilot(job['installer_id'])
            apiStatus = job['status']
            location = self.get_station_name(job['facility_id'])
            typeName = self.get_item(job['blueprint_type_id'])
            endDate = job['end_date']
            d0 = datetime.datetime.strptime(
                job['end_date'], '%Y-%m-%d %H:%M:%S')
            d1 = datetime.datetime.utcnow()
            delta = d0 - d1
            timeLeft = self.strfdelta(delta, "{days}d {hours}h {minutes}m")
            # check for updates
            selfStatus = self.get_or_set(jobID, apiStatus)
            if selfStatus != apiStatus:
                self.send(self.build_identifier(self.config['REPORT_INDUSTRY_CHAN']),
                          ":factory: Update: {} in {} by {} {} --> {}".format(
                    typeName, location, installer, selfStatus, apiStatus))

            # check for new
            if self['last_job_id'] < job['job_id']:
                self['last_job_id'] = job['job_id']
                self.send(self.build_identifier(self.config['REPORT_INDUSTRY_CHAN']),
                          ":factory: New: {} by {} in {} ends {} timeleft {}".format(
                    typeName, installer, location, endDate, timeLeft))

    def _poller_pos_check(self):
        for corp in self.get_corps():
            for starbase in self.get_starbases(corp['corporationID']):

                if self.check_outdated(starbase) and self.check_warning(starbase['itemID'], 'warn_outdated'):
                    self.set_warning(
                        starbase['itemID'], 'warn_outdated', False)
                    self.logger.info(
                        "Reported outdated warning on {}".format(starbase['moonName']))
                    self.send(self.build_identifier(self.config['REPORT_POS_CHAN']), '%s %s %s is outdated.' % (
                        corp['ticker'], starbase['moonName'], starbase['starbaseTypeName']))

                if self.check_fuel(starbase) and self.check_warning(starbase['itemID'], 'warn_fuel'):
                    self.set_warning(starbase['itemID'], 'warn_fuel', False)
                    self.logger.info(
                        "Reported fuel warning on {}".format(starbase['moonName']))
                    self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                              '%s %s %s  will run out of fuel in %s hours' % (
                                  corp['ticker'], starbase['moonName'], starbase['starbaseTypeName'],
                                  round(starbase['fuelBlocks'] / starbase['baseFuelUsage'])))

                if self.check_reinforced(starbase) and self.check_warning(starbase['itemID'], 'warn_reinforced'):
                    self.set_warning(
                        starbase['itemID'], 'warn_reinforced', False)
                    self.logger.info(
                        "Reported reinforced warning on {}".format(starbase['moonName']))
                    self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                              '%s %s %s got reinforced, Timer %s' % (
                                  corp['ticker'], starbase['moonName'], starbase['starbaseTypeName'],
                                  starbase['stateTimeStamp']))

                if self.check_stront(starbase) and self.check_warning(starbase['itemID'], 'warn_stront'):
                    self.set_warning(starbase['itemID'], 'warn_stront', False)
                    self.logger.info(
                        "Reported stront warning on {}".format(starbase['moonName']))
                    self.send(self.build_identifier(self.config['REPORT_POS_CHAN']),
                              '%s %s %s has only stront for %s hours' % (
                                  corp['ticker'], starbase['moonName'], starbase['starbaseTypeName'],
                                  round(starbase['strontium'] / starbase['baseStrontUsage'])))

    def _poller_pos_clear_warnings(self):
        for corp in self.get_corps():
            for starbase in self.get_starbases(corp['corporationID']):

                if not self.check_fuel(starbase) and not self.check_warning(starbase['itemID'], 'warn_fuel'):
                    self.set_warning(starbase['itemID'], 'warn_fuel', True)
                    self.logger.info(
                        "Reenabled fuel warning on {}".format(starbase['moonName']))

                if not self.check_stront(starbase) and not self.check_warning(starbase['itemID'], 'warn_stront'):
                    self.set_warning(starbase['itemID'], 'warn_stront', True)
                    self.logger.info(
                        "Reenabled stront warning on {}".format(starbase['moonName']))

                if not self.check_outdated(starbase) and not self.check_warning(starbase['itemID'], 'warn_outdated'):
                    self.set_warning(starbase['itemID'], 'warn_outdated', True)
                    self.logger.info(
                        "Reenabled outdated warning on {}".format(starbase['moonName']))

                if not self.check_reinforced(starbase) and not self.check_warning(starbase['itemID'],
                                                                                  'warn_reinforced'):
                    self.set_warning(
                        starbase['itemID'], 'warn_reinforced', True)
                    self.logger.info(
                        "Reenabled reinforced warning on {}".format(starbase['moonName']))

    ####################################################################################################################
    # bot commands

    @botcmd
    def jobs_all(self, msg, args):
        """Prints out all industry jobs"""
        if args != '':
            yield 'Usage: !jobs all'
        for job in self.get_industry(self.config['CORP_ID']):
            # cast some vars
            installer = self.get_pilot(job['installer_id'])
            location = self.get_station_name(job['facility_id'])
            typeName = self.get_item(job['blueprint_type_id'])
            endDate = job['end_date']
            d0 = datetime.datetime.strptime(
                job['end_date'], '%Y-%m-%d %H:%M:%S')
            d1 = datetime.datetime.utcnow()
            delta = d0 - d1
            timeLeft = self.strfdelta(delta, "{days}d {hours}h {minutes}m")
            yield ":factory: {} in {} by {}, ends on {}, timeleft: {}".format(
                typeName, location, installer, endDate, timeLeft)

    @botcmd
    def pos_find(self, msg, args):
        """Finds all towers in given <system>, Usage !pos find <system>"""
        if args == '':
            yield 'Usage: !pos find <system>'
            return
        results = 0
        for corp in self.get_corps():
            for starbase in self.get_starbases(corp['corporationID']):
                if starbase['solarSystemName'].lower() == args.lower():
                    results += 1
                    yield "**Location:** %s **Type:** %s **Corp:** %s " % (
                        starbase['moonName'], starbase['starbaseTypeName'], corp['ticker'])
        if results == 0:
            yield "Found no towers in %s" % args

    @botcmd
    def poco_find(self, msg, args):
        """Finds all pocos in given <system>, Usage !poco find <system>"""
        if args == '':
            yield 'Usage: !poco find <system>'
            return
        results = 0
        for corp in self.get_corps():
            for poco in self.get_pocos(corp['corporationID']):
                if poco['solarSystemName'].lower() == args.lower():
                    results += 1
                    yield "**Location:** %s **Type:** %s **Corp:** %s" % (
                        poco['planetName'], poco['planetTypeName'], corp['ticker'])
        if results == 0:
            yield "Found no pocos in %s" % args

    @botcmd
    def pos_oof(self, msg, args):
        """Finds all towers that will be running out of fuel in the given timeframe, Usage: !pos oof <hours>"""
        if args == '' or args.isdigit() is False:
            yield 'Usage: !pos oof <hours>'
            return
        results = 0
        for corp in self.get_corps():
            for starbase in self.get_starbases(corp['corporationID']):
                hours_left = starbase['fuelBlocks'] / starbase['baseFuelUsage']
                if int(hours_left) < int(args) and int(hours_left) != 0:
                    results += 1
                    yield "**Location:** %s **Type:** %s **Corp:** %s **Hours of fuel left:** %s" % (
                        starbase['moonName'], starbase['starbaseTypeName'], corp['ticker'], round(hours_left))
        if results == 0:
            yield "Found no offline towers."

    @botcmd
    def pos_reinforced(self, msg, args):
        """Finds all reinforced towers , Usage: !pos reinforced"""
        if args != '':
            yield 'Usage: !pos reinforced'
            return
        results = 0
        for corp in self.get_corps():
            for starbase in self.get_starbases(corp['corporationID']):
                if starbase['state'] == 3:
                    results += 1
                    yield "%s - %s - %s. Timer: %s" % (
                        starbase['moonName'], starbase['starbaseTypeName'], corp['ticker'], starbase['stateTimeStamp'])
        if results == 0:
            yield "Did not find any reinforced towers."

    @botcmd
    def pos_oos(self, msg, args):
        """Finds all towers that have no stront, Usage: !pos oos"""
        if args != '':
            yield 'Usage: !pos oos'
            return
        results = 0
        for corp in self.get_corps():
            for starbase in self.get_starbases(corp['corporationID']):
                if starbase['strontium'] == 0 and starbase['state'] == 4:
                    results += 1
                    yield "**Location:** %s **Type:** %s **Corp:** %s has no strontium." % (
                        starbase['moonName'], starbase['starbaseTypeName'], corp['ticker'])
        if results == 0:
            yield "Found no towers without stront."

    @botcmd
    def pos_offline(self, msg, args):
        """Finds all offline towers, Usage: !pos offline"""
        if args != '':
            yield 'Usage: !pos offline'
            return
        results = 0
        for corp in self.get_corps():
            for starbase in self.get_starbases(['corporationID']):
                if starbase['state'] == 1 or starbase['state'] == 0:
                    results += 1
                    yield "**Location:** %s **Type:** %s **Corp:** %s" % (
                        starbase['moonName'], starbase['starbaseTypeName'], corp['ticker'])
        if results == 0:
            yield "found no offline towers."

    @botcmd(admin_only=True)
    def pos_clearwarnings(self, msg, args):
        """Clears all saved warning states"""
        if args != '':
            return "Usage !pos clearwarnings"
        for item in self:
            del self[item]
        return "Cleared all saved warning states."

    @botcmd(admin_only=True, hidden=True)
    def pos_clearwarningspos(self, msg, args):
        """Trigger _poller_pos_clear_warnings"""
        self._poller_pos_clear_warnings()

    @botcmd(admin_only=True, hidden=True)
    def pos_checkpos(self, msg, args):
        """Trigger _poller_pos_check"""
        self._poller_pos_check()

    @botcmd(admin_only=True, hidden=True)
    def trigger_trades(self, msg, args):
        self._poller_transactions_check()

    @botcmd(admin_only=True, hidden=True)
    def trigger_industry(self, msg, args):
        self._poller_industry_check()

    @botcmd(admin_only=True, hidden=True)
    def trigger_contracts(self, msg, args):
        self._poller_contracts_check()
