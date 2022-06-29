import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import List

from pycoingecko import CoinGeckoAPI

import src.HmyTx_Constants as C
import src.HmyTx_Utils as HmyUtil


class KoinlyTrade():
    '''
    Description:
        Class to hold all information for a koinly transaction.
    BeAware:
    Inputs:
        Timestamp: POSIX timestamp, seconds from epoch
        txHash: etherium hash for transaction
    Notes:
        Fee are not in withdraw / deposit transactions.
        Fee can have cost label if no trade occurs.
        Transfers between accounts are matched when they are:
            12hrs apart,
            20% less than sent,
            txHash blank on one or both or same.
    ToDo:
    '''

    time: str
    timeStamp: int
    sent: float = 0
    sentCoin: str = ''

    received: float = 0
    receivedCoin: str = ''

    fee: float = 0
    feeCoin: str = ''

    value: float = 0
    valueCoin: str = ''

    label: str = ''
    notes: str = ''
    txHash: str
    lpTokenList = []

    def __init__(self, timestamp: int, txHash: str) -> None:
        dTime = datetime.fromtimestamp(timestamp)
        self.timeStamp = timestamp
        self.time = dTime.strftime("%Y-%m-%d %H:%M:%S") + ' UTC'
        self.txHash = txHash

    def tidyTokenNAme(self, tokenSym) -> str:
        if tokenSym[:3] == 'bsc':
            tokenSym = tokenSym[3:]
        if tokenSym[:4] == '1USD':
            tokenSym = tokenSym[1:]
        if tokenSym[:3] == 'DFK' or tokenSym[:2] == '0x':
            if tokenSym not in self.lpTokenList:
                self.lpTokenList.append(str(tokenSym))

            for i, sym in enumerate(self.lpTokenList):
                if tokenSym == sym:
                    tokenSym = 'NULL' + str(i+1)
                    break
            #tokenSym = 'NULL' + str(count)

        return tokenSym

    def UpdateTrade(self, trade):
        'Updates sent / received and value.'
        if trade[C.TFT_SENTAMOOUNT] != '':
            self.sent = trade[C.TFT_SENTAMOOUNT]
            self.sentCoin = trade[C.TFT_SENTTOKEN]
        elif trade[C.TFT_RECAMOUNT] != '':
            self.received = trade[C.TFT_RECAMOUNT]
            self.receivedCoin = trade[C.TFT_RECTOKEN]
        else:
            self.value = trade[C.TFT_TAMOUNT]
            self.valueCoin = trade[C.TFT_TNAME]
        #self.notes += f'{trade[C.TFT_CSVLABEL]} {trade[C.TFT_TOPIC]} {trade[C.TFT_THEIR]}'

    def KoinlyString(self) -> str:
        'Date,Sent Amount,Sent Currency,Received Amount,Received Currency,Fee Amount,Fee Currency,Net Worth Amount,Net Worth Currency,Label,Description,TxHash\n'
        if self.sent == 0 and self.received == 0:
            print(f"Error! no coins sent or received! {self.value} {self.valueCoin} {self.txHash}")
            return ''
        else:
            msgOut = self.time + ','
            if self.sent != 0:
                msgOut += f'{self.sent},{self.tidyTokenNAme(self.sentCoin)},'
            else:
                msgOut += ',,'

            if self.received != 0:
                msgOut += f'{self.received},{self.tidyTokenNAme(self.receivedCoin)},'
            else:
                msgOut += ',,'

            if self.fee != 0:
                msgOut += f'{self.fee},{self.feeCoin},'
            else:
                msgOut += ',,'

            if self.value != 0:
                msgOut += f'{self.value},{self.valueCoin},'
            else:
                msgOut += ',,'

            msgOut += self.label + ','
            msgOut += self.notes + ','
            msgOut += self.txHash + '\n'

            return msgOut


class KoinlyProcessor():
    priceErrors = {}

    allProcessedTxs = []


    def __init__(self, _oneAddressList: List[str]) -> None:
        if len(_oneAddressList) > 0:
            for addr in _oneAddressList:
                self.oneAddress = addr
                if self.oneAddress[:2] == '0x':
                    self.oneAddress = HmyUtil.convert_hex_to_one(addr)

                self.outputDirectory = f'./TransactionHistory/'
                self.outputJSONFile = f'{self.outputDirectory}{self.oneAddress}.json'

                self.allTransactions = {}
                if os.path.exists(self.outputJSONFile):
                    with open(self.outputJSONFile, 'r') as f:
                        self.allTransactions = json.loads(f.read())

                self.tokenBook = self.updateCoinGeckoTokenList()

                self.marketData = self.getCoinGeckoHistory(self.tokenBook)

                self.allProcessedTxs.extend(self.ProcessTransactions())
                self.printUnknown()

            self.makeCSV(self.allProcessedTxs,'AllAccounts')

    def getSuperFineGeckoID(self, cg, tokenBook, contract,timestampOldest,timestampNewest):
        tsFin = timestampNewest
        tsStart = timestampNewest - int(23.9*60*60)

        time.sleep(2)
        FinehistoryDataUS = cg.get_coin_market_chart_range_by_id(
            tokenBook[contract][C.CG_ID],  'usd', str(tsStart), str(tsFin))

        time.sleep(2)
        FinehistoryDataAU = cg.get_coin_market_chart_range_by_id(
            tokenBook[contract][C.CG_ID],  'aud', str(tsStart), str(tsFin))

        tsFin = tsStart
        tsStart = tsFin - int(23.9*60*60)

        while tsFin > timestampOldest:
            time.sleep(2)
            FinehistoryDataUS_new = cg.get_coin_market_chart_range_by_id(
                tokenBook[contract][C.CG_ID],  'usd', str(tsStart), str(tsFin))

            FinehistoryDataUS["prices"].extend(
                FinehistoryDataUS_new["prices"])
            FinehistoryDataUS["market_caps"].extend(
                FinehistoryDataUS_new["market_caps"])
            FinehistoryDataUS["total_volumes"].extend(
                FinehistoryDataUS_new["total_volumes"])

            time.sleep(2)
            FinehistoryDataAU_new = cg.get_coin_market_chart_range_by_id(
                tokenBook[contract][C.CG_ID],  'aud', str(tsStart), str(tsFin))

            FinehistoryDataAU["prices"].extend(
                FinehistoryDataAU_new["prices"])
            FinehistoryDataAU["market_caps"].extend(
                FinehistoryDataAU_new["market_caps"])
            FinehistoryDataAU["total_volumes"].extend(
                FinehistoryDataAU_new["total_volumes"])

            tsFin = tsStart
            tsStart = tsFin - int(23.9*60*60)

        return (FinehistoryDataUS,FinehistoryDataAU)

    def getFineGeckoID(self, cg, tokenBook, contract,timestampOldest,timestampNewest):
        tsFin = timestampNewest
        tsStart = timestampNewest - 89*24*60*60

        time.sleep(2)
        FinehistoryDataUS = cg.get_coin_market_chart_range_by_id(
            tokenBook[contract][C.CG_ID],  'usd', str(tsStart), str(tsFin))

        time.sleep(2)
        FinehistoryDataAU = cg.get_coin_market_chart_range_by_id(
            tokenBook[contract][C.CG_ID],  'aud', str(tsStart), str(tsFin))

        tsFin = tsStart
        tsStart = tsFin - 89*24*60*60

        while tsFin > timestampOldest:
            time.sleep(2)
            FinehistoryDataUS_new = cg.get_coin_market_chart_range_by_id(
                tokenBook[contract][C.CG_ID],  'usd', str(tsStart), str(tsFin))

            FinehistoryDataUS["prices"].extend(
                FinehistoryDataUS_new["prices"])
            FinehistoryDataUS["market_caps"].extend(
                FinehistoryDataUS_new["market_caps"])
            FinehistoryDataUS["total_volumes"].extend(
                FinehistoryDataUS_new["total_volumes"])

            time.sleep(2)
            FinehistoryDataAU_new = cg.get_coin_market_chart_range_by_id(
                tokenBook[contract][C.CG_ID],  'aud', str(tsStart), str(tsFin))

            FinehistoryDataAU["prices"].extend(
                FinehistoryDataAU_new["prices"])
            FinehistoryDataAU["market_caps"].extend(
                FinehistoryDataAU_new["market_caps"])
            FinehistoryDataAU["total_volumes"].extend(
                FinehistoryDataAU_new["total_volumes"])

            tsFin = tsStart
            tsStart = tsFin - 89*24*60*60

        return (FinehistoryDataUS,FinehistoryDataAU)

    def getFineContract(self, cg, tokenBook, contract,timestampOldest,timestampNewest):
        tsFin = timestampNewest
        tsStart = timestampNewest - 89*24*60*60

        time.sleep(2)
        FinehistoryDataUS = cg.get_coin_market_chart_range_from_contract_address_by_id(
            tokenBook[contract][C.CG_CHAINID], tokenBook[contract][C.CG_CONTRACT], 'usd', str(tsStart), str(tsFin))

        time.sleep(2)
        FinehistoryDataAU = cg.get_coin_market_chart_range_from_contract_address_by_id(
            tokenBook[contract][C.CG_CHAINID], tokenBook[contract][C.CG_CONTRACT], 'aud', str(tsStart), str(tsFin))

        tsFin = tsStart
        tsStart = tsFin - 89*24*60*60

        while tsFin > timestampOldest:
            time.sleep(2)
            FinehistoryDataUS_new = cg.get_coin_market_chart_range_from_contract_address_by_id(
                tokenBook[contract][C.CG_CHAINID], tokenBook[contract][C.CG_CONTRACT], 'usd', str(tsStart), str(tsFin))

            FinehistoryDataUS["prices"].extend(FinehistoryDataUS_new["prices"])
            FinehistoryDataUS["market_caps"].extend(FinehistoryDataUS_new["market_caps"])
            FinehistoryDataUS["total_volumes"].extend(FinehistoryDataUS_new["total_volumes"])

            time.sleep(2)
            FinehistoryDataAU_new = cg.get_coin_market_chart_range_from_contract_address_by_id(
                tokenBook[contract][C.CG_CHAINID], tokenBook[contract][C.CG_CONTRACT], 'aud', str(tsStart), str(tsFin))

            FinehistoryDataAU["prices"].extend(FinehistoryDataAU_new["prices"])
            FinehistoryDataAU["market_caps"].extend(FinehistoryDataAU_new["market_caps"])
            FinehistoryDataAU["total_volumes"].extend(FinehistoryDataAU_new["total_volumes"])

            tsFin = tsStart
            tsStart = tsFin - 89*24*60*60

        return (FinehistoryDataUS,FinehistoryDataAU)

    def getSuperFineHistory(self, contract, tokenBook):
        cg = CoinGeckoAPI()

        timestampNow = int(time.time())
        dateTimeStart = datetime(2021, 1, 1)
        timestamp = dateTimeStart.replace(
            tzinfo=timezone.utc).timestamp()
        timestampStart = int(timestamp)
        maxAttempts = 10
        attempts = 0
        while attempts < maxAttempts:
            try:
                coinBase = f'./HistoryData/{contract}'
                coinPath = coinBase + '.json'
                if (C.CG_ISONLINE in tokenBook[contract] and tokenBook[contract][C.CG_ISONLINE]):
                    'Check api to update info.'
                    print(f'{attempts}: Checking {tokenBook[contract][C.CG_NAME]} : {contract}')

                    if(os.path.exists(coinPath)):
                        print(f"\tHave data on file.")
                        with open(coinPath, 'r') as f:
                            CoinInfo = json.loads(f.read())

                            if C.C_SFINE_USD not in CoinInfo:
                                (FinehistoryDataUS_new,FinehistoryDataAU_new)= self.getSuperFineGeckoID(cg, tokenBook, contract,timestampStart,timestampNow)

                                FinehistoryDataUS_new["prices"] = sorted(FinehistoryDataUS_new["prices"])
                                FinehistoryDataUS_new["market_caps"] = sorted(FinehistoryDataUS_new["market_caps"])
                                FinehistoryDataUS_new["total_volumes"] = sorted(FinehistoryDataUS_new["total_volumes"])

                                FinehistoryDataAU_new["prices"] = sorted(FinehistoryDataAU_new["prices"])
                                FinehistoryDataAU_new["market_caps"] = sorted(FinehistoryDataAU_new["market_caps"])
                                FinehistoryDataAU_new["total_volumes"] = sorted(FinehistoryDataAU_new["total_volumes"])

                                CoinInfo.update({C.C_SFINE_USD:FinehistoryDataUS_new})
                                CoinInfo.update({C.C_SFINE_AUD:FinehistoryDataAU_new})

                                with open(coinPath, 'w') as f:
                                    json.dump(CoinInfo, f,ensure_ascii=False, indent=4)

                                print("Added Superfine Data")
                            else:
                                'has Superfine data. update that shit!'
                            
            except Exception as e:
                if e.__context__ is None and '429' in e.__str__():
                    delay = 5
                    print(f'Too many request! will pause for {delay} seconds.')
                    attempts += 1
                    time.sleep(delay)
                elif '404' in e.__context__.__str__():
                    print('Could not find in CoinGecko API')
                    if tokenBook[contract][C.CG_ISONLINE]:
                        tokenBook[contract][C.CG_ISONLINE] = False
                    attempts = maxAttempts
                else:
                    print('String" ', e.__str__())
                    print('Type" ', sys.exc_info()[0])
                    print('Context: ', e.__context__)
                    print('Value" ', sys.exc_info()[1])
                    print('Trace" ', sys.exc_info()[2])

    def getCoinGeckoHistory(self, tokenBook) -> dict:
        cg = CoinGeckoAPI()

        marketData = {}

        timestampNow = int(time.time())
        dateTimeStart = datetime(2021, 1, 1)
        timestamp = dateTimeStart.replace(
            tzinfo=timezone.utc).timestamp()
        timestampStart = int(timestamp)

        # Const.TXOUTPATH + f'TokenContracts_{oneAddress}.json'
        maxAttempts = 10
        
        for contract in tokenBook:
            attempts = 0
            while attempts < maxAttempts:
                try:
                    coinBase = f'./HistoryData/{contract}'
                    coinPath = coinBase + '.json'
                    hasInAPI = True
                    if C.CG_ISONLINE not in tokenBook[contract]:
                        print(f'{attempts}: Updating {tokenBook[contract][C.CG_NAME]} : {contract}')
                        print('No data for contract. Will make new.')
                        tokenBook[contract] = {
                            C.CG_CHAINID: "harmony-shard-0",
                            C.CG_CONTRACT: contract,
                            C.CG_NAME: tokenBook[contract],
                            C.CG_ISONLINE: hasInAPI}

                    if (C.CG_ISONLINE in tokenBook[contract] and tokenBook[contract][C.CG_ISONLINE]):
                        'Check api to update info.'
                        print(f'{attempts}: Checking {tokenBook[contract][C.CG_NAME]} : {contract}')
                        haveAdded = False
                        if C.CG_ID in tokenBook[contract]:
                            "use the gecko id not id/contract info."
                            if(not os.path.exists(coinPath)):
                                print('Have not downloaded info. Will do it now.')

                                time.sleep(2)
                                coins = (cg.get_coin_by_id(id=tokenBook[contract][C.CG_ID]))

                                (FinehistoryDataUS,FinehistoryDataAU)= self.getFineGeckoID( cg, tokenBook, contract,timestampStart,timestampNow)

                                FinehistoryDataUS["prices"] = sorted(FinehistoryDataUS["prices"])
                                FinehistoryDataUS["market_caps"] = sorted(FinehistoryDataUS["market_caps"])
                                FinehistoryDataUS["total_volumes"] = sorted(FinehistoryDataUS["total_volumes"])

                                FinehistoryDataAU["prices"] = sorted(FinehistoryDataAU["prices"])
                                FinehistoryDataAU["market_caps"] = sorted(FinehistoryDataAU["market_caps"])
                                FinehistoryDataAU["total_volumes"] = sorted(FinehistoryDataAU["total_volumes"])

                                coinsInfo = {
                                    C.C_INFO: coins,
                                    C.C_COARSE_USD: AllhistoryDataUS,
                                    C.C_COARSE_AUD: AllhistoryDataAU,
                                    C.C_FINE_USD: FinehistoryDataUS,
                                    C.C_FINE_AUD: FinehistoryDataAU,
                                    C.C_OLDTIME : timestampStart,
                                    C.C_NEWTIME : timestampNow}

                                with open(coinPath, 'w') as f:
                                    json.dump(coinsInfo, f,
                                            ensure_ascii=False, indent=4)

                                marketData.update({coinBase: coinsInfo})
                            else:
                                'Has market data file!'
                                print(f"\tHave data on file.")
                                with open(coinPath, 'r') as f:
                                    marketData.update({coinBase: json.loads(f.read())})
                             
                                oldestDate = marketData[coinBase][C.C_OLDTIME]
                                newestDate = marketData[coinBase][C.C_NEWTIME]

                                timeTillNow = timestampNow - newestDate
                                timeTillStart = oldestDate - timestampStart
                                if timeTillNow > 24*60*60: #Magic number 1 day in milliseconds
                                    print(f"Updating time till now.")
                                    (FinehistoryDataUS_new,FinehistoryDataAU_new)= self.getFineGeckoID(cg, tokenBook, contract,newestDate,timestampNow)
                                    
                                    marketData[coinBase][C.C_FINE_USD]["prices"].extend(FinehistoryDataUS_new["prices"])
                                    marketData[coinBase][C.C_FINE_USD]["market_caps"].extend(FinehistoryDataUS_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_USD]["total_volumes"].extend(FinehistoryDataUS_new["total_volumes"])

                                    marketData[coinBase][C.C_FINE_AUD]["prices"].extend(FinehistoryDataAU_new["prices"])
                                    marketData[coinBase][C.C_FINE_AUD]["market_caps"].extend(FinehistoryDataAU_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_AUD]["total_volumes"].extend(FinehistoryDataAU_new["total_volumes"])
                                    marketData[coinBase][C.C_NEWTIME] = timestampNow
                                    haveAdded = True
                                    print(f"\tCaught up to today. Added {timeTillNow/(60*60)} hrs.")

                                if timeTillStart > 24*60*60: #Magic number 1 day in milliseconds
                                    print(f"Updating time till {dateTimeStart.strftime('%Y-%m-%d %H:%M:%S')}.")
                                    (FinehistoryDataUS_new,FinehistoryDataAU_new)= self.getFineGeckoID(cg, tokenBook, contract,timestampStart,oldestDate)
                                    
                                    marketData[coinBase][C.C_FINE_USD]["prices"].extend(FinehistoryDataUS_new["prices"])
                                    marketData[coinBase][C.C_FINE_USD]["market_caps"].extend(FinehistoryDataUS_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_USD]["total_volumes"].extend(FinehistoryDataUS_new["total_volumes"])

                                    marketData[coinBase][C.C_FINE_AUD]["prices"].extend(FinehistoryDataAU_new["prices"])
                                    marketData[coinBase][C.C_FINE_AUD]["market_caps"].extend(FinehistoryDataAU_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_AUD]["total_volumes"].extend(FinehistoryDataAU_new["total_volumes"])
                                    marketData[coinBase][C.C_OLDTIME] = timestampStart
                                    haveAdded = True
                                    print(f"\tCaught up to {dateTimeStart.strftime('%Y-%m-%d %H:%M:%S')}. Added {timeTillStart/(60*60)} hrs.")

                                if haveAdded:
                                    marketData[coinBase][C.C_FINE_USD]["prices"] = sorted(marketData[coinBase][C.C_FINE_USD]["prices"])
                                    marketData[coinBase][C.C_FINE_USD]["market_caps"] = sorted(marketData[coinBase][C.C_FINE_USD]["market_caps"])
                                    marketData[coinBase][C.C_FINE_USD]["total_volumes"] = sorted(marketData[coinBase][C.C_FINE_USD]["total_volumes"])

                                    marketData[coinBase][C.C_FINE_AUD]["prices"] = sorted(marketData[coinBase][C.C_FINE_AUD]["prices"])
                                    marketData[coinBase][C.C_FINE_AUD]["market_caps"] = sorted(marketData[coinBase][C.C_FINE_AUD]["market_caps"])
                                    marketData[coinBase][C.C_FINE_AUD]["total_volumes"] = sorted(marketData[coinBase][C.C_FINE_AUD]["total_volumes"])
                        else:
                            'use id/contract info'
                            if(not os.path.exists(coinPath)):
                                print('Have not downloaded info. Will do it now.')

                                time.sleep(2)
                                coins = (cg.get_coin_info_from_contract_address_by_id(
                                    id=tokenBook[contract][C.CG_CHAINID], contract_address=tokenBook[contract][C.CG_CONTRACT]))

                                time.sleep(2)
                                AllhistoryDataUS = cg.get_coin_market_chart_range_from_contract_address_by_id(
                                    tokenBook[contract][C.CG_CHAINID], tokenBook[contract][C.CG_CONTRACT], 'usd', str(timestampStart), str(timestampNow))

                                time.sleep(2)
                                AllhistoryDataAU = cg.get_coin_market_chart_range_from_contract_address_by_id(
                                    tokenBook[contract][C.CG_CHAINID], tokenBook[contract][C.CG_CONTRACT], 'aud', str(timestampStart), str(timestampNow))

                                
                                (FinehistoryDataUS,FinehistoryDataAU)= self.getFineContract(cg, tokenBook, contract,timestampStart,timestampNow)

                                FinehistoryDataUS["prices"] = sorted(FinehistoryDataUS["prices"])
                                FinehistoryDataUS["market_caps"] = sorted(FinehistoryDataUS["market_caps"])
                                FinehistoryDataUS["total_volumes"] = sorted(FinehistoryDataUS["total_volumes"])

                                FinehistoryDataAU["prices"] = sorted(FinehistoryDataAU["prices"])
                                FinehistoryDataAU["market_caps"] = sorted(FinehistoryDataAU["market_caps"])
                                FinehistoryDataAU["total_volumes"] = sorted(FinehistoryDataAU["total_volumes"])

                                coinsInfo = {
                                    C.C_INFO: coins,
                                    C.C_COARSE_USD: AllhistoryDataUS,
                                    C.C_COARSE_AUD: AllhistoryDataAU,
                                    C.C_FINE_USD: FinehistoryDataUS,
                                    C.C_FINE_AUD: FinehistoryDataAU,
                                    C.C_OLDTIME : timestampStart,
                                    C.C_NEWTIME : timestampNow}

                                with open(coinPath, 'w') as f:
                                    json.dump(coinsInfo, f,ensure_ascii=False, indent=4)
                                marketData.update({coinBase: coinsInfo})
                            else:
                                'Has market data file!'
                                print(f"\tHave data on file.")
                                with open(coinPath, 'r') as f:
                                    marketData.update({coinBase: json.loads(f.read())})

                                oldestDate = marketData[coinBase][C.C_OLDTIME]
                                newestDate = marketData[coinBase][C.C_NEWTIME]

                                timeTillNow = timestampNow - newestDate
                                timeTillStart = oldestDate - timestampStart
                                if timeTillNow > 24*60*60: #Magic number 1 day in milliseconds
                                    print(f"Updating time till now.")
                                    (FinehistoryDataUS_new,FinehistoryDataAU_new)= self.getFineContract(cg, tokenBook, contract,newestDate,timestampNow)
                                    
                                    marketData[coinBase][C.C_FINE_USD]["prices"].extend(FinehistoryDataUS_new["prices"])
                                    marketData[coinBase][C.C_FINE_USD]["market_caps"].extend(FinehistoryDataUS_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_USD]["total_volumes"].extend(FinehistoryDataUS_new["total_volumes"])

                                    marketData[coinBase][C.C_FINE_AUD]["prices"].extend(FinehistoryDataAU_new["prices"])
                                    marketData[coinBase][C.C_FINE_AUD]["market_caps"].extend(FinehistoryDataAU_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_AUD]["total_volumes"].extend(FinehistoryDataAU_new["total_volumes"])
                                    marketData[coinBase][C.C_NEWTIME] = timestampNow
                                    haveAdded = True
                                    print(f"\tCaught up to today. Added {timeTillNow/(60*60)} hrs.")


                                if timeTillStart > 24*60*60: #Magic number 1 day in milliseconds
                                    print(f"Updating time till {dateTimeStart.strftime('%Y-%m-%d %H:%M:%S')}.")
                                    (FinehistoryDataUS_new,FinehistoryDataAU_new)= self.getFineContract(cg, tokenBook, contract,timestampStart,oldestDate)
                                    
                                    marketData[coinBase][C.C_FINE_USD]["prices"].extend(FinehistoryDataUS_new["prices"])
                                    marketData[coinBase][C.C_FINE_USD]["market_caps"].extend(FinehistoryDataUS_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_USD]["total_volumes"].extend(FinehistoryDataUS_new["total_volumes"])

                                    marketData[coinBase][C.C_FINE_AUD]["prices"].extend(FinehistoryDataAU_new["prices"])
                                    marketData[coinBase][C.C_FINE_AUD]["market_caps"].extend(FinehistoryDataAU_new["market_caps"])
                                    marketData[coinBase][C.C_FINE_AUD]["total_volumes"].extend(FinehistoryDataAU_new["total_volumes"])
                                    marketData[coinBase][C.C_OLDTIME] = timestampStart
                                    haveAdded = True
                                    print(f"\tCaught up to {dateTimeStart.strftime('%Y-%m-%d %H:%M:%S')}. Added {timeTillStart/(60*60)} hrs.")

                        if C.C_OLDTIME not in marketData[coinBase]:
                            marketData[coinBase].update({C.C_OLDTIME : timestampStart})
                            haveAdded = True

                        if C.C_NEWTIME not in marketData[coinBase]:
                            marketData[coinBase].update({C.C_NEWTIME : timestampNow})
                            haveAdded = True

                        if haveAdded:
                            marketData[coinBase][C.C_FINE_USD]["prices"] = sorted(marketData[coinBase][C.C_FINE_USD]["prices"])
                            marketData[coinBase][C.C_FINE_USD]["market_caps"] = sorted(marketData[coinBase][C.C_FINE_USD]["market_caps"])
                            marketData[coinBase][C.C_FINE_USD]["total_volumes"] = sorted(marketData[coinBase][C.C_FINE_USD]["total_volumes"])

                            marketData[coinBase][C.C_FINE_AUD]["prices"] = sorted(marketData[coinBase][C.C_FINE_AUD]["prices"])
                            marketData[coinBase][C.C_FINE_AUD]["market_caps"] = sorted(marketData[coinBase][C.C_FINE_AUD]["market_caps"])
                            marketData[coinBase][C.C_FINE_AUD]["total_volumes"] = sorted(marketData[coinBase][C.C_FINE_AUD]["total_volumes"])



                            with open(coinPath, 'w') as f:
                                json.dump(marketData[coinBase], f,ensure_ascii=False, indent=4)
                                
                            print(f"\tUpdated  {tokenBook[contract][C.CG_NAME]} : {contract}")
                        
                        attempts = maxAttempts
                    else:
                        (f'{contract} not in CoinGecko')
                        attempts = maxAttempts

                except Exception as e:
                    if e.__context__ is None and '429' in e.__str__():
                        delay = 5
                        print(f'Too many request! will pause for {delay} seconds.')
                        attempts += 1
                        time.sleep(delay)
                    elif '404' in e.__context__.__str__():
                        print('Could not find in CoinGecko API')
                        if tokenBook[contract][C.CG_ISONLINE]:
                            tokenBook[contract][C.CG_ISONLINE] = False
                        attempts = maxAttempts
                    else:
                        print('String" ', e.__str__())
                        print('Type" ', sys.exc_info()[0])
                        print('Context: ', e.__context__)
                        print('Value" ', sys.exc_info()[1])
                        print('Trace" ', sys.exc_info()[2])

            if contract == "0xcf664087a5bb0237a0bad6742852ec6c8d69a27a":
                'self.getSuperFineHistory(contract, tokenBook)'

        with open(C.CG_CONTRACTPATH, 'w') as f:
            json.dump(tokenBook, f, ensure_ascii=False, indent=4)
        cg.session.close()

        PathBase = './HistoryData/'
        historyTokenPaths = os.listdir(PathBase)

        for Path in historyTokenPaths:
            with open(PathBase+Path, 'r') as f:
                if Path[:-5] not in marketData:
                    marketData.update({Path[:-5]: json.loads(f.read())})

        return marketData

    def updateCoinGeckoTokenList(self) -> dict:
        '''
        Description:
            updates a list of tokens found in the transactions.
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        hexAddr = HmyUtil.convert_one_to_hex(self.oneAddress)
        topicAddr = hexAddr[2:].lower()

        tokenBook = {}
        addressPath = f'./TokenInfo/CoinGeckoContracts.json'

        if os.path.exists(addressPath):
            with open(addressPath, 'r') as f:
                tokenBook = json.loads(f.read())

        for i, txHash in enumerate(self.allTransactions[C.TRANSACTIONS_KEY]):
            tx = self.allTransactions[C.TRANSACTIONS_KEY][txHash]

            if 'Receipt' in tx and 'status' in tx['Receipt'] and tx['Receipt']['status'] != 0:
                #  transactionInfo = {'time','name','code','gas','to','from','trades','unknownTrades','label'}
                #       Trade keys = {'from','to','sentAmount','sentToken','receivedAmount','receivedToken','topic','label'}
                tr = HmyUtil.getTransferInfo(tx, self.oneAddress)

                for trade in tr[C.TF_TRADES]:
                    'add to token list'
                    tokenName = trade[C.TFT_RECTOKEN]
                    if trade[C.TFT_SENTTOKEN] != '':
                        tokenName = trade[C.TFT_SENTTOKEN]

                    if trade[C.TFT_TCONT] not in tokenBook:
                        tokenBook[trade[C.TFT_TCONT]] = {
                            C.CG_CHAINID: "harmony-shard-0",
                            C.CG_CONTRACT: trade[C.TFT_TCONT],
                            C.CG_NAME: tokenName,
                            C.CG_ISONLINE: True}

        with open(addressPath, 'w', encoding='utf-8') as f:
            json.dump(tokenBook, f, ensure_ascii=False, indent=4)

        return tokenBook

    def processWAGMI(self,Wagmitades: List[KoinlyTrade],trades: List[KoinlyTrade]) -> List[KoinlyTrade]:
        
        extraTrades: List[KoinlyTrade] = []
        for trade in trades:
            if 'WAGMI' in trade.sentCoin or 'WAGMI' in trade.receivedCoin:
                extraTrades.append(trade)
        for trade in extraTrades:
            trades.remove(trade)
        extraTrades.extend(Wagmitades) 
        sortedTrades = sorted(extraTrades, key=lambda d: d.timeStamp) 

        runningWagmi = 0
        runningSWag = 0
        newTrades = []
        for trade in sortedTrades:
            if runningWagmi < (1 * (10 ** -9)):
                runningWagmi = 0
            if 'deposit' in trade.label:
                runningWagmi += trade.received
                trade.label = ''
            elif 'reward' in trade.label:
                if (runningWagmi + 1 * 10 ** -9) >= trade.received:
                    trade.sent = trade.received
                    trade.sentCoin = "WAGMI"
                    trade.label = 'Matched'
                    trade.fee = runningWagmi
                    runningWagmi -= trade.received
                    trade.feeCoin = runningWagmi
                        
                elif runningWagmi != 0:
                    print(f'Error: got more wagmi than deposited.')
                    trade.sent = runningWagmi
                    trade.sentCoin = "WAGMI"
                    newTrade = KoinlyTrade(trade.timeStamp-10,trade.txHash)
                    newTrade.received = trade.received - runningWagmi
                    newTrade.receivedCoin = trade.receivedCoin
                    newTrade.label = 'reward'
                    newTrades.append(newTrade)

                    trade.received = runningWagmi
                    trade.label = ''
                    runningWagmi = 0
                else:
                    print("got other thing")
            else:
                trade.label = ''

            #trade.fee = 0
            #trade.feeCoin = ''

            if 'sWAGMI' == trade.sentCoin:
                runningSWag -= trade.sent
            elif 'sWAGMI' == trade.receivedCoin:
                runningSWag += trade.received

            if runningSWag < (-1 * (10 ** -8)):
                newTrade = KoinlyTrade(trade.timeStamp-15,trade.txHash) # magic number is seconds earlier
                newTrade.received = -runningSWag
                newTrade.receivedCoin = 'sWAGMI'
                newTrade.label = 'reward'
                price = self.getPrice(self.marketData, '0x0dc78c79b4eb080ead5c1d16559225a46b580694',self.tokenBook, newTrade.timeStamp*1000)  #Hash is WAGMI contract

                if price[1] != 0:
                    newTrade.value = price[1] * newTrade.received
                    newTrade.valueCoin = 'AUD'
                newTrade.notes += f"| ${newTrade.value} | Matched: {str(price[2])[:-3]} Real: {newTrade.timeStamp} "

                newTrades.append(newTrade)
                runningSWag = 0

        
        sortedTrades.extend(newTrades)
        sortedTrades.sort(key=lambda d: d.timeStamp) 
        return sortedTrades

    def getKoinlyTrade(self, tr, timestamp, txHash) -> KoinlyTrade:
        if len(tr[C.TF_SORTTRADES]) == 1:
            jTrade = tr[C.TF_SORTTRADES][0]
            trade = KoinlyTrade(int(timestamp), txHash)
            trade.UpdateTrade(jTrade)

            
            price = self.getPrice(self.marketData, jTrade[C.TFT_TCONT],self.tokenBook, timestamp*1000)

            trade.notes += f"| ${price[1]*jTrade[C.TFT_TAMOUNT]} | Matched: {str(price[2])[:-3]} Real: {timestamp} "

            if trade.value == 0:
                if price[1] != 0:
                    if jTrade[C.TFT_SENTAMOOUNT] != '':
                        trade.value = price[1] * jTrade[C.TFT_SENTAMOOUNT]
                    else:
                        trade.value = price[1] * jTrade[C.TFT_RECAMOUNT]

                    trade.valueCoin = 'AUD'

            return trade
        elif len(tr[C.TF_SORTTRADES]) == 2:
            trade = KoinlyTrade(int(timestamp), txHash)
            for jTrade in tr[C.TF_SORTTRADES]:
                trade.UpdateTrade(jTrade)
                trade.fee = tr[C.TF_GAS]
                trade.feeCoin = "ONE"

                price = self.getPrice(self.marketData, jTrade[C.TFT_TCONT],self.tokenBook, timestamp*1000)

                trade.notes += f"{jTrade[C.TFT_TOPIC]}| ${price[1]*jTrade[C.TFT_TAMOUNT]} | Matched: {str(price[2])[:-3]} Real: {timestamp} "

                if trade.value == 0:
                    if price[1] != 0:
                        if jTrade[C.TFT_SENTAMOOUNT] != '':
                            trade.value = price[1] * jTrade[C.TFT_SENTAMOOUNT]
                        else:
                            trade.value = price[1] * jTrade[C.TFT_RECAMOUNT]

                        trade.valueCoin = 'AUD'
            return trade
        else:
            #print(f'Koinly {tr[C.TF_FUNCLABEL]}: Length {len(tr[C.TF_SORTTRADES])}. Tx: {txHash}')
            for jTrade in tr[C.TF_SORTTRADES]:
                print(f'\t{jTrade[C.TFT_RECAMOUNT]} {jTrade[C.TFT_SENTAMOOUNT]} {jTrade[C.TFT_TNAME]}')

    def makeKoinlyTrades(self, trades, timestamp, txHash):
        tradesOut = []
        for jTrade in trades:
            trade = KoinlyTrade(int(timestamp), txHash)
            trade.UpdateTrade(jTrade)

            price = self.getPrice(self.marketData, jTrade[C.TFT_TCONT],self.tokenBook, timestamp*1000)
            trade.notes += f"{jTrade[C.TFT_TOPIC]} | ${price[1]*jTrade[C.TFT_TAMOUNT]} | Matched: {str(price[2])[:-3]} Real: {timestamp} "

            if trade.value == 0:
                if price[1] != 0:
                    trade.value = price[1] 
                    trade.valueCoin = 'AUD'
            tradesOut.append(trade)
        return tradesOut
    def makeCSV(self, processedTxs,addon):

        koinlyCSV = 'Date,Sent Amount,Sent Currency,Received Amount,Received Currency,Fee Amount,Fee Currency,Net Worth Amount,Net Worth Currency,Label,Description,TxHash\n'

        tx: KoinlyTrade
        for tx in processedTxs:
            koinlyCSV += tx.KoinlyString()

        with open(f'./CSV Outputs/testKoinly_{addon}{self.oneAddress}.csv', 'w') as f:
            f.write(koinlyCSV)

    def printUnknown(self) -> list:
        ''
        unprocessedNotification = []
        transactionInfo: List[KoinlyTrade] = []
        wagamiInfo: List[KoinlyTrade] = []
        unProcessed: List[KoinlyTrade] = []
        for i, txHash in enumerate(self.allTransactions[C.TRANSACTIONS_KEY]):
            tx = self.allTransactions[C.TRANSACTIONS_KEY][txHash]

            if 'Receipt' in tx and 'status' in tx['Receipt'] and tx['Receipt']['status'] != 0:
                #  transactionInfo = {'time','name','code','gas','to','from','trades','unknownTrades','label'}
                #       Trade keys = {'from','to','sentAmount','sentToken','receivedAmount','receivedToken','topic','label'}
                tr = HmyUtil.getTransferInfo(tx, self.oneAddress)

                unProcessed.extend(self.makeKoinlyTrades(tr[C.TF_SORTTRADES],tx[C.T_TX_KEY]['timestamp'], txHash))
                unProcessed.extend(self.makeKoinlyTrades(tr[C.TF_UKTRADES],tx[C.T_TX_KEY]['timestamp'], txHash))

        self.makeCSV(unProcessed,'Unknown')

    def ProcessTransactions(self) -> list:
        '''
        Description:
            Processess all transactions. Will make dictionary with Koinly items for each transaction.
            'Date,Sent Amount,Sent Currency,Received Amount,Received Currency,Fee Amount,Fee Currency,Net Worth Amount,Net Worth Currency,Label,Description,TxHash'
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        unprocessedNotification = []
        transactionInfo: List[KoinlyTrade] = []
        wagamiInfo: List[KoinlyTrade] = []
        unProcessed: List[KoinlyTrade] = []
        for i, txHash in enumerate(self.allTransactions[C.TRANSACTIONS_KEY]):
            tx = self.allTransactions[C.TRANSACTIONS_KEY][txHash]

            if 'Receipt' in tx and 'status' in tx['Receipt'] and tx['Receipt']['status'] != 0:
                #  transactionInfo = {'time','name','code','gas','to','from','trades','unknownTrades','label'}
                #       Trade keys = {'from','to','sentAmount','sentToken','receivedAmount','receivedToken','topic','label'}
                tr = HmyUtil.getTransferInfo(tx, self.oneAddress)

                if 'LP' in tr[C.TF_FUNCLABEL]:
                    if 'Swap' in tr[C.TF_FUNCLABEL]:
                        'LP tokens get swap label for koinly CSV'
                        (rewards, LPs) = self.sumRewards(
                            tr[C.TF_TRADES], tx[C.T_TX_KEY]['timestamp']*1000)
                        for rewardName in rewards:
                            trade = KoinlyTrade(
                                int(tx[C.T_TX_KEY]['timestamp']), txHash)
                            trade.label = 'realized gain'
                            trade.notes = f"{rewards[rewardName][C.TFT_TCONT]} {rewards[rewardName]['price'][2]}"
                            if rewards[rewardName]['price'][1] != 0:
                                trade.value = rewards[rewardName]['price'][1]
                                trade.valueCoin = 'AUD'

                            if rewards[rewardName]['amount'] > 0:
                                trade.received = rewards[rewardName]['amount']
                                trade.receivedCoin = rewardName
                                trade.value *= rewards[rewardName]['amount']
                            else:
                                trade.sent = -rewards[rewardName]['amount']
                                trade.sentCoin = rewardName
                                trade.value *= (-rewards[rewardName]
                                                ['amount'])
                            transactionInfo.append(trade)

                        for lp in LPs:
                            trade = KoinlyTrade(
                                int(tx[C.T_TX_KEY]['timestamp']), txHash)
                            trade.label = 'swap'
                            trade.notes = f"{lp[C.TFT_TCONT]}"
                            trade.UpdateTrade(lp)
                            if trade.sent == 0:
                                trade.receivedCoin = lp[C.TFT_TCONT]
                                trade.label = 'unstake'   
                            else:
                                trade.sentCoin = lp[C.TFT_TCONT]
                                trade.label = 'stake'
                            transactionInfo.append(trade)

                    elif 'Split' in tr[C.TF_FUNCLABEL]:
                        'split LP in half, add trade with other tokens'
                        if len(tr[C.TF_SORTTRADES]) == 3:
                            trades = (KoinlyTrade(int(tx[C.T_TX_KEY]['timestamp']), txHash), 
                                      KoinlyTrade(int(tx[C.T_TX_KEY]['timestamp']), txHash))
                            count = 0
                            for jTrade in tr[C.TF_SORTTRADES]:
                                if jTrade[C.TFT_SENTAMOOUNT] != '':
                                    'lp token'
                                    trades[0].sent = trades[1].sent = float(jTrade[C.TFT_SENTAMOOUNT])/2
                                    trades[0].sentCoin = trades[1].sentCoin = jTrade[C.TFT_TCONT]
                                else:
                                    trades[count].received = jTrade[C.TFT_RECAMOUNT]
                                    trades[count].receivedCoin = jTrade[C.TFT_RECTOKEN]
                                    trades[count].fee = tr[C.TF_GAS]/2
                                    trades[count].feeCoin = "ONE"

                                    price = self.getPrice(self.marketData, jTrade[C.TFT_TCONT], self.tokenBook,tx[C.T_TX_KEY]['timestamp']*1000)

                                    trades[count].notes = f"| ${price[1]*jTrade[C.TFT_TAMOUNT]} | Matched: {str(price[2])[:-3]} Real: {tx[C.T_TX_KEY]['timestamp']} "

                                    if trades[count].value == 0:
                                        if price[1] != 0:
                                            trades[count].value =price[1] * jTrade[C.TFT_RECAMOUNT]
                                            trades[0].valueCoin = trades[1].valueCoin = 'AUD'
                                    count += 1
                            trades[0].label = trades[1].label = 'liquidity out'
                            transactionInfo.append(trades[0])
                            transactionInfo.append(trades[1])
                        else:    
                            print(f'Split {tr[C.TF_FUNCLABEL]}: Length {len(tr[C.TF_SORTTRADES])}. Tx: {txHash}')
                            for jTrade in tr[C.TF_SORTTRADES]:
                                print(f'\t{jTrade[C.TFT_RECAMOUNT]} {jTrade[C.TFT_SENTAMOOUNT]} {jTrade[C.TFT_TNAME]}')

                    elif 'Join' in tr[C.TF_FUNCLABEL]:
                        'split LP in half, add trade with other tokens'
                        if len(tr[C.TF_SORTTRADES]) == 3:
                            trades = (KoinlyTrade(
                                int(tx[C.T_TX_KEY]['timestamp']), txHash), KoinlyTrade(
                                int(tx[C.T_TX_KEY]['timestamp']), txHash))
                            count = 0
                            for jTrade in tr[C.TF_SORTTRADES]:

                                if jTrade[C.TFT_RECAMOUNT] != '':
                                    'lp token'
                                    trades[0].received = trades[1].received = jTrade[C.TFT_RECAMOUNT]/2
                                    trades[0].receivedCoin = trades[1].receivedCoin = jTrade[C.TFT_TCONT]
                                else:
                                    'other tokens'
                                    trades[count].sent = jTrade[C.TFT_SENTAMOOUNT]
                                    trades[count].sentCoin = jTrade[C.TFT_SENTTOKEN]
                                    trades[count].fee = tr[C.TF_GAS]/2
                                    trades[count].feeCoin = "ONE"

                                    price = self.getPrice(self.marketData, jTrade[C.TFT_TCONT],self.tokenBook, tx[C.T_TX_KEY]['timestamp']*1000)

                                    trades[count].notes = f"| ${price[1]*jTrade[C.TFT_TAMOUNT]} | Matched: {str(price[2])[:-3]} Real: {tx[C.T_TX_KEY]['timestamp']} "

                                    if trades[count].value == 0:
                                        if price[1] != 0:
                                            trades[count].value = price[1] * jTrade[C.TFT_SENTAMOOUNT]
                                            trades[count].valueCoin = 'AUD'
                                    count += 1
                            trades[0].label = trades[1].label = 'liquidity in'
                            transactionInfo.append(trades[0])
                            transactionInfo.append(trades[1])
                        else:
                            print(f'Join {tr[C.TF_FUNCLABEL]}: Length {len(tr[C.TF_SORTTRADES])}. Tx: {txHash}')
                            for jTrade in tr[C.TF_SORTTRADES]:
                                print(f'\t{jTrade[C.TFT_RECAMOUNT]} {jTrade[C.TFT_SENTAMOOUNT]} {jTrade[C.TFT_TNAME]}')
                    else:
                        print('Not LP Swap, LP Join or LP Split')

                elif 'Claim' == tr[C.TF_FUNCLABEL]:
                    (rewards, LPs) = self.sumRewards(
                        tr[C.TF_TRADES], tx[C.T_TX_KEY]['timestamp']*1000)
                    for rewardName in rewards:
                        trade = KoinlyTrade(
                            int(tx[C.T_TX_KEY]['timestamp']), txHash)
                        trade.label = 'realized gain'
                        trade.notes = f"{rewards[rewardName][C.TFT_TCONT]} at {rewards[rewardName]['price'][2]/1000} at {tx[C.T_TX_KEY]['timestamp']}"
                        if rewards[rewardName]['price'][1] != 0:
                            trade.value = rewards[rewardName]['price'][1]
                            trade.valueCoin = 'AUD'

                        if rewards[rewardName]['amount'] > 0:
                            trade.received = rewards[rewardName]['amount']
                            trade.receivedCoin = rewardName
                            trade.value *= rewards[rewardName]['amount']
                        else:
                            trade.sent = -rewards[rewardName]['amount']
                            trade.sentCoin = rewardName
                            trade.value *= (-rewards[rewardName]
                                            ['amount'])
                        transactionInfo.append(trade)
                
                elif 'DFK' in tr[C.TF_FUNCLABEL]:
                    if tr[C.TF_FUNCLABEL] not in unprocessedNotification:
                        print((f'{tr[C.TF_FUNCLABEL]} label not processed.'))
                        unprocessedNotification.append(tr[C.TF_FUNCLABEL])

                    if 'Stake' in tr[C.TF_FUNCLABEL]:
                        (f'{tr[C.TF_FUNCLABEL]} label not processed.')
                    else:
                        (f'{tr[C.TF_FUNCLABEL]} label not processed.')

                elif 'WAGMI' in tr[C.TF_FUNCLABEL]:
                    tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                    if tradeOut is not None:
                        if 'Deposit' in tr[C.TF_FUNCLABEL]:
                            tradeOut.label = 'deposit'
                        if 'Claim' in tr[C.TF_FUNCLABEL]:
                            tradeOut.label = 'reward'
                        if tradeOut is not None:
                            wagamiInfo.append(tradeOut)
                elif 'Transfer' in tr[C.TF_FUNCLABEL]:
                    tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                    if tradeOut is not None:
                        transactionInfo.append(tradeOut)
                    #print("Got Transfer")
                elif 'Trade' in tr[C.TF_FUNCLABEL]:
                    tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                    if tradeOut is not None:
                        transactionInfo.append(tradeOut)
                    #print("Got Trade")
                else:
                    match tr[C.TF_FUNCLABEL]:
                        case "Donation":
                            if len(tr[C.TF_SORTTRADES]) == 1:
                                jTrade = tr[C.TF_SORTTRADES][0]
                                trade = KoinlyTrade(int(tx[C.T_TX_KEY]['timestamp']), txHash)
                                trade.notes = f"Transfer {jTrade[C.TFT_TCONT]}"
                                trade.label = 'gift'
                                trade.UpdateTrade(jTrade)

                                price = self.getPrice(self.marketData, jTrade[C.TFT_TCONT],self.tokenBook, tx[C.T_TX_KEY]['timestamp']*1000)

                                trade.notes += f"${price[1]} AUD at {price[2]/1000} at {tx[C.T_TX_KEY]['timestamp']}"

                                if trade.value == 0:
                                    if price[1] != 0:
                                        if jTrade[C.TFT_SENTAMOOUNT] != '':
                                            trade.value = price[1] * jTrade[C.TFT_SENTAMOOUNT]
                                        else:
                                            trade.value = price[1] * jTrade[C.TFT_RECAMOUNT]

                                        trade.valueCoin = 'AUD'

                                transactionInfo.append(trade)
                            else:
                                print(f'{tr[C.TF_FUNCLABEL]}: Length {len(tr[C.TF_SORTTRADES])}. Tx: {txHash}')
                                for jTrade in tr[C.TF_SORTTRADES]:
                                    print(f'Donation \t{jTrade[C.TFT_RECAMOUNT]} {jTrade[C.TFT_SENTAMOOUNT]} {jTrade[C.TFT_TNAME]}')

                        case "Frey":
                            if tr[C.TF_FUNCLABEL] not in unprocessedNotification:
                                print((f'{tr[C.TF_FUNCLABEL]} label not processed.'))
                                unprocessedNotification.append(tr[C.TF_FUNCLABEL])
                            tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                            if tradeOut is not None:
                                tradeOut.label = tr[C.TF_FUNCLABEL]
                                unProcessed.append(tradeOut)
                        case "Sonic":
                            if tr[C.TF_FUNCLABEL] not in unprocessedNotification:
                                print((f'{tr[C.TF_FUNCLABEL]} label not processed.'))
                                unprocessedNotification.append(tr[C.TF_FUNCLABEL])
                            tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                            if tradeOut is not None:
                                tradeOut.label = tr[C.TF_FUNCLABEL]
                                unProcessed.append(tradeOut)
                        case "Tranquil":
                            if tr[C.TF_FUNCLABEL] not in unprocessedNotification:
                                print((f'{tr[C.TF_FUNCLABEL]} label not processed.'))
                                unprocessedNotification.append(tr[C.TF_FUNCLABEL])
                            tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                            if tradeOut is not None:
                                tradeOut.label = tr[C.TF_FUNCLABEL]
                                unProcessed.append(tradeOut)
                        case "Cosmic":
                            if tr[C.TF_FUNCLABEL] not in unprocessedNotification:
                                print((f'{tr[C.TF_FUNCLABEL]} label not processed.'))
                                unprocessedNotification.append(tr[C.TF_FUNCLABEL])
                            tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                            if tradeOut is not None:
                                tradeOut.label = tr[C.TF_FUNCLABEL]
                                unProcessed.append(tradeOut)
                        case "Kitties":
                            if tr[C.TF_FUNCLABEL] not in unprocessedNotification:
                                print((f'{tr[C.TF_FUNCLABEL]} label not processed.'))
                                unprocessedNotification.append(tr[C.TF_FUNCLABEL])
                            tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                            if tradeOut is not None:
                                tradeOut.label = tr[C.TF_FUNCLABEL]
                                unProcessed.append(tradeOut)
                        case _:
                            if tr[C.TF_FUNCLABEL] not in unprocessedNotification:
                                print((f'{tr[C.TF_FUNCLABEL]} label not processed.'))
                                unprocessedNotification.append(tr[C.TF_FUNCLABEL])
                            tradeOut = self.getKoinlyTrade(tr, tx[C.T_TX_KEY]['timestamp'], txHash)
                            if tradeOut is not None:
                                tradeOut.label = tr[C.TF_FUNCLABEL]
                                unProcessed.append(tradeOut)
        
        print('Need to get earlier price data for the following:')
        for cont in self.priceErrors:
            it = self.priceErrors[cont]
            dTime = datetime.fromtimestamp(float(it["timeStamp"])/1000)
            mTime = datetime.fromtimestamp(float(it["matched"])/1000)
            print(f'\tNeed {it["time"]/(1000*60*60):0.2f} hrs earlier -- {it["symbol"]} -- Have {mTime.strftime("%Y-%m-%d %H:%M:%S")} not {dTime.strftime("%Y-%m-%d %H:%M:%S")} : {it["contract"]}')
        updatesWags = self.processWAGMI(wagamiInfo,transactionInfo)
        transactionInfo.extend(updatesWags)
        self.makeCSV(transactionInfo,'')
        self.makeCSV(updatesWags,'WAGMI')

        return transactionInfo

    def sumRewards(self, transactions, timestamp) -> tuple[dict, list]:
        rewards = {}
        LPs = []
        for trade in transactions:
            'get the name, get the amount'

            price = self.getPrice(self.marketData, trade[C.TFT_TCONT],self.tokenBook, timestamp)

            name = trade[C.TFT_RECTOKEN]
            amount = trade[C.TFT_RECAMOUNT]
            if trade[C.TFT_SENTTOKEN] != '':
                name = trade[C.TFT_SENTTOKEN]
                amount = -trade[C.TFT_SENTAMOOUNT]

            # Only checking if LP in name... might have other option.
            if 'LP' not in name:
                if name not in rewards:
                    rewards.update({name: {
                                    'amount': amount,
                                    C.TFT_TCONT: trade[C.TFT_TCONT],
                                    'price': price}})
                else:
                    rewards[name]['amount'] += amount
            else:
                'LP token'
                LPs.append(trade)

        return (rewards, LPs)

    def getPrice(self, historyData, contract, contractBook, timestamp):
        if contract in contractBook and contractBook[contract][C.CG_CONTRACT] != contract:
            contract = contractBook[contract][C.CG_CONTRACT]
        if contract in historyData:
            matchedTime = historyData[contract]['FineUSD']['prices'][-1][0]
            USprice = historyData[contract]['FineUSD']['prices'][-1][1]
            AUprice = historyData[contract]['FineAUD']['prices'][-1][1]

            for i, timest in enumerate(historyData[contract]['FineUSD']['prices']):
                if timest[0] > timestamp:
                    matchedTime = historyData[contract]['FineUSD']['prices'][i][0]
                    if i > 0:
                        USprice = (historyData[contract]['FineUSD']['prices'][i][1] + historyData[contract]['FineUSD']['prices'][i][1])/2
                        AUprice = (historyData[contract]['FineAUD']['prices'][i][1] + historyData[contract]['FineUSD']['prices'][i][1])/2
                    else:
                        USprice = historyData[contract]['FineUSD']['prices'][i][1]
                        AUprice = historyData[contract]['FineAUD']['prices'][i][1]
                    break
            
            if abs(matchedTime-timestamp) > 1000*60*60*6:
                if contract not in self.priceErrors:
                    #print(f"Time {abs(matchedTime-timestamp)/ (1000*60*60)} hr apart {historyData[contract]['CoinInfo']['name']} {matchedTime} not {timestamp}")
                    self.priceErrors.update({contract:{'time':abs(matchedTime-timestamp),
                                                        'name':historyData[contract]['CoinInfo']['name'],
                                                        'symbol':historyData[contract]['CoinInfo']['symbol'],
                                                        'contract':contract,
                                                        'timeStamp': timestamp,
                                                        'matched': matchedTime}})
                else:
                    if self.priceErrors[contract]['time'] < abs(matchedTime-timestamp):
                        self.priceErrors[contract]['time'] = abs(matchedTime-timestamp)
                        self.priceErrors[contract]['timeStamp'] = timestamp
                        self.priceErrors[contract]['matched'] = matchedTime
                return(0, 0, matchedTime)
            else:
                return (USprice, AUprice, matchedTime)
        else:
            return(0, 0, timestamp)

julianAddy1 = 'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3'
julianAddy2 = 'one1nzvl9a558tp54qw773xs6yeutkshqg3my5mksz'
julianAddy3 = 'one1vzw8vmjeplfcjf8w0fdlkt6g26et4tj462sn4n'

accounts = [julianAddy1,julianAddy2,julianAddy3]
#KoinlyProcessor(julianAddy1)
#KoinlyProcessor(julianAddy2)
#KoinlyProcessor([julianAddy3])
#KoinlyProcessor('0xf9358cc0b2a2b8f20da1edd5d385e2d59a5370e3')
#KoinlyProcessor('one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3')
