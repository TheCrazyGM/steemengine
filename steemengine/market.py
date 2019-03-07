from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import sys
from datetime import datetime, timedelta, date
import time
import io
import json
import requests
from timeit import default_timer as timer
import logging
from steemengine.api import Api
from steemengine.tokens import Tokens
from steemengine.wallet import Wallet
from steemengine.exceptions import (TokenDoesNotExists, TokenNotInWallet, InsufficientTokenAmount)
from beem.instance import shared_steem_instance
from beem.account import Account


class Market(list):
    """ Access the steem-engine market

        :param Steem steem_instance: Steem
               instance
    """
    def __init__(self, steem_instance=None):
        self.api = Api()
        self.steem = steem_instance or shared_steem_instance()
        self.tokens = Tokens()
        self.refresh()

    def refresh(self):
        super(Market, self).__init__(self.get_metrics())

    def get_metrics(self):
        """Returns all token within the wallet as list"""
        metrics = self.api.find("market", "metrics", query={})
        return metrics

    def get_buy_book(self, symbol, account=None, limit=100, offset=0):
        if self.tokens.get_token(symbol) is None:
            raise TokenDoesNotExists("%s does not exists" % symbol)
        if account is None:
            buy_book = self.api.find("market", "buyBook", query={"symbol": symbol.upper()}, limit=limit, offset=offset)
        else:
            buy_book = self.api.find("market", "buyBook", query={"symbol": symbol.upper(), "account": account}, limit=limit, offset=offset)
        return buy_book

    def get_sell_book(self, symbol, account=None, limit=100, offset=0):
        if self.tokens.get_token(symbol) is None:
            raise TokenDoesNotExists("%s does not exists" % symbol)
        if account is None:
            sell_book = self.api.find("market", "sellBook", query={"symbol": symbol.upper()}, limit=limit, offset=offset)
        else:
            sell_book = self.api.find("market", "sellBook", query={"symbol": symbol.upper(), "account": account}, limit=limit, offset=offset)
        return sell_book

    def get_trades_history(self, symbol, account=None, limit=30, offset=0):
        if self.tokens.get_token(symbol) is None:
            raise TokenDoesNotExists("%s does not exists" % symbol)
        if account is None:
            trades_history = self.api.find("market", "tradesHistory", query={"symbol": symbol.upper()}, limit=limit, offset=offset)
        else:
            trades_history = self.api.find("market", "tradesHistory", query={"symbol": symbol.upper(), "account": account}, limit=limit, offset=offset)
        return trades_history

    def withdraw(self, account, amount):
        """Widthdraw STEEMP to account as STEEM.

            :param str account: account name
            :param float amount: Amount to withdraw

            Withdraw example:

            .. code-block:: python

                from steemengine.market import Market
                from beem import Steem
                active_wif = "5xxxx"
                stm = Steem(keys=[active_wif])
                market = Market(steem_instance=stm)
                market.withdraw("test", 1)
        """
        wallet = Wallet(account, steem_instance=self.steem)
        token = wallet.get_token("STEEMP")
        if token is None:
            raise TokenNotInWallet("%s is not in wallet." % "STEEMP")
        if float(token["balance"]) < float(amount):
            raise InsufficientTokenAmount("Only %.3f in wallet" % float(token["balance"]))
        contractPayload = {"quantity":str(amount)}
        json_data = {"contractName":"steempegged","contractAction":"withdraw",
                     "contractPayload":contractPayload}
        tx = self.steem.custom_json("ssc-mainnet1", json_data, required_auths=[account])
        return tx

    def deposit(self, account, amount):
        """Deposit STEEM to market in exchange for STEEMP.

            :param str account: account name
            :param float amount: Amount to deposit

            Deposit example:

            .. code-block:: python

                from steemengine.market import Market
                from beem import Steem
                active_wif = "5xxxx"
                stm = Steem(keys=[active_wif])
                market = Market(steem_instance=stm)
                market.deposit("test", 1)
        """
        acc = Account(account, steem_instance=self.steem)
        steem_balance = acc.get_balance("available", "STEEM")
        if float(steem_balance) < float(amount):
            raise InsufficientTokenAmount("Only %.3f in wallet" % float(steem_balance))       
        json_data = '{"id":"ssc-mainnet1","json":{"contractName":"steempegged","contractAction":"buy","contractPayload":{}}}' 
        tx = acc.transfer("steem-peg", amount, "STEEM", memo=json_data)
        return tx

    def buy(self, account, amount, symbol, price):
        """Buy token for given price.

            :param str account: account name
            :param float amount: Amount to withdraw
            :param str symbol: symbol
            :param float price: price

            Buy example:

            .. code-block:: python

                from steemengine.market import Market
                from beem import Steem
                active_wif = "5xxxx"
                stm = Steem(keys=[active_wif])
                market = Market(steem_instance=stm)
                market.buy("test", 1, "ENG", 0.95)
        """
        wallet = Wallet(account, steem_instance=self.steem)
        token = wallet.get_token("STEEMP")
        if token is None:
            raise TokenNotInWallet("%s is not in wallet." % "STEEMP")
        if float(token["balance"]) < float(amount) * float(price):
            raise InsufficientTokenAmount("Only %.3f in wallet" % float(token["balance"]))
        contractPayload = {"symbol": symbol.upper(), "quantity":str(amount), "price": str(price)}
        json_data = {"contractName":"market","contractAction":"buy",
                     "contractPayload":contractPayload}
        tx = self.steem.custom_json("ssc-mainnet1", json_data, required_auths=[account])
        return tx

    def sell(self, account, amount, symbol, price):
        """Sell token for given price.

            :param str account: account name
            :param float amount: Amount to withdraw
            :param str symbol: symbol
            :param float price: price

            Sell example:

            .. code-block:: python

                from steemengine.market import Market
                from beem import Steem
                active_wif = "5xxxx"
                stm = Steem(keys=[active_wif])
                market = Market(steem_instance=stm)
                market.sell("test", 1, "ENG", 0.95)
        """
        wallet = Wallet(account, steem_instance=self.steem)
        token = wallet.get_token(symbol)
        if token is None:
            raise TokenNotInWallet("%s is not in wallet." % symbol)
        if float(token["balance"]) < float(amount):
            raise InsufficientTokenAmount("Only %.3f in wallet" % float(token["balance"]))
        contractPayload = {"symbol": symbol.upper(), "quantity":str(amount), "price": str(price)}
        json_data = {"contractName":"market","contractAction":"sell",
                     "contractPayload":contractPayload}
        tx = self.steem.custom_json("ssc-mainnet1", json_data, required_auths=[account])
        return tx

    def cancel(self, account, order_type, order_id):
        """Cancel buy/sell order.

            :param str account: account name
            :param str order_type: sell or buy
            :param int order_id: order id

            Cancel example:

            .. code-block:: python

                from steemengine.market import Market
                from beem import Steem
                active_wif = "5xxxx"
                stm = Steem(keys=[active_wif])
                market = Market(steem_instance=stm)
                market.sell("test", "sell", 12)
        """

        contractPayload = {"type": order_type, "id": order_id}
        json_data = {"contractName":"market","contractAction":"cancel",
                     "contractPayload":contractPayload}
        tx = self.steem.custom_json("ssc-mainnet1", json_data, required_auths=[account])
        return tx