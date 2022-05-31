import json
import os
import re
import sys
import time
from datetime import datetime
from functools import lru_cache
from tokenize import Number

import requests
from bech32 import bech32_decode, bech32_encode
from codetiming import Timer
from eth_utils import to_checksum_address, to_hex
# from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from web3 import Web3
from web3.auto import w3

import src.HmyTx_Constants as Const
from src.lib.pyhmy.pyhmy import account, transaction, util

# logFilePath = './log.txt'
"""
test_net = 'https://api.s0.b.hmny.io'				# this is shard 0
test_net_shard_1 = 'https://api.s1.b.hmny.io'
test_address = 'one18t4yj4fuutj83uwqckkvxp9gfa0568uc48ggj7'

Const.MAINNET0 = 'https://rpc.s0.t.hmny.io'
Const.MAINNET0_shard_1 = 'https://rpc.s1.t.hmny.io'

Const.MAINNET02 = 'https://a.api.s0.t.hmny.io'
Const.ENDPOINT = 'https://explorer-v2-api.hmny.io/v0/'

ethONE = '0xcf664087a5bb0237a0bad6742852ec6c8d69a27a'

Const.UNKNOWNFUNCTION = 'Unknown'
Const.UNDEFINEDFUNCTION = 'Undefined'
NoEntry = 'NoEntry'

ChainHarmonyKey = '0x63564c40'
ChainDFKKey = '0xd2af'
"""
HRC20Tokens = {}


def check_if_in_list_of_dict(sample_dict, key, value):
    """Check if given value exists in list of dictionaries """

    for elem in sample_dict:
        if value == elem[key]:
            return True
    return False


def getBalance(oneAddy) -> float:
    balance = 0
    count = 0
    while balance == 0:
        try:
            count = count+1
            balance = account.get_balance(oneAddy, endpoint=Const.MAINNET0)
            balance = balance/pow(10, 18)

            with open('log.txt', 'a') as f:
                f.write(str(balance))
                f.write('\n')
            # print('Balance = '+ str(balance) + 'ONE')
        except:
            # print('No connection... Attempt '+str(count) + ' Balance = '+ str(balance))
            with open('log.txt', 'a') as f:
                f.write('No connection... Attempt '+str(count))
                f.write('\n')
            time.sleep(1)
    return balance


def getTransactionCount(oneAddy) -> float:

    if oneAddy[:2] == '0x':
        oneAddy = convert_hex_to_one(oneAddy)

    expectedTXs = account.get_transactions_count(
        oneAddy, tx_type='ALL', endpoint=Const.MAINNET0)
    return expectedTXs


def updateFunctionList(outputFile, allTxs) -> dict:
    '''
    Description:
    BeAware:
    Inputs:
    Output:
    Notes:
    ToDo:
    '''
    with open('log.txt', 'a') as f:
        f.write(f"\nAdding Metamask functions to transactions")
    print("\n")
    print(f'Adding Metamask functions to {outputFile}')

    functionsOut = {}

    if os.path.exists(outputFile):
        with open(outputFile, 'r') as f:
            functionsOut = json.loads(f.read())

    for tx in allTxs:
        if len(tx['input']) >= 10:
            if tx['input'][0:10] not in functionsOut:
                functionsOut[tx['input'][0:10]] = {
                    "name": Const.UNDEFINEDFUNCTION}
            # else:
                # print('input is in list.')
        elif tx['input'] == '0x':
            if tx['input'] not in functionsOut:
                functionsOut[tx['input']] = {"name": 'Burn'}
            # else:
                # print('input is in list.')
        else:
            print(f"No Input function! got '{tx['input']}'")
            # functionsOut[tx['input']] = {"name": Const.UNKNOWNFUNCTION}

    with open(outputFile, 'w', encoding='utf-8') as f:
        f.write(json.dumps(functionsOut, ensure_ascii=False, indent=4))

    return functionsOut


def getHRC20(oneAddy, pageIndex, pageSize) -> list:
    bucketSize = pageSize
    url = f'{Const.ENDPOINT}shard/0/address/{convert_one_to_hex(oneAddy).lower()}/transactions/type/erc20?offset={pageIndex*bucketSize}&limit={bucketSize}'
    response = requests.get(url)
    jsonResponse = json.loads(response.text)
    hrc20Ts = []
    if response.status_code == 200:
        hrc20Ts.extend(jsonResponse)
    else:
        print(
            f'Bucket {pageIndex}: Error... Status code: {response.status_code}')

    return hrc20Ts


def getBaseInfo(tx, oneAddress):
    '''
    Output keys: {'time','name','code','gas','to','from'}
    '''
    timestamp = datetime.fromtimestamp(tx[Const.TX_KEY]['timestamp'])
    timestr = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    fnName = tx[Const.FUNCTION_KEY]['function']
    fnCode = tx[Const.FUNCTION_KEY]['code']
    gasFee = tx[Const.TX_KEY]['gasPrice'] * \
        tx[Const.RECEIPT_KEY]['gasUsed'] / (10 ** 18)

    fromAddr = tx[Const.TX_KEY]['from']
    toAddr = tx[Const.TX_KEY]['to']

    if fromAddr == oneAddress:
        fromAddr = fromAddr + ' (me)'
        toAddr = toAddr + ' (them)'
    elif toAddr == oneAddress:
        toAddr = toAddr + ' (me)'
        fromAddr = fromAddr + ' (them)'
    else:
        print('Error not in to or from!')

    return {
        'time': timestr,
        'name': fnName,
        'code': fnCode,
        'gas': gasFee,
        'to': toAddr,
        'from': fromAddr}


def getTransferInfo(tx, oneAddress):
    '''
    Output keys: {'from','amount','token','to','topic'}
    '''
    global HRC20Tokens
    if len(list(HRC20Tokens.keys())) == 0:
        HRC20Tokens = writeAllTokensToFile(Const.HRC20LISTPATH)
    hexAddr = convert_one_to_hex(oneAddress)
    topicAddr = hexAddr[2:].lower()
    fromAddr = convert_one_to_hex(tx[Const.TX_KEY]['from'])[2:].lower()
    toAddr = convert_one_to_hex(tx[Const.TX_KEY]['to'])[2:].lower()
    transactionsOut = []
    unknownTxOut = []

    value = tx[Const.TX_KEY]['value'] / (10 ** 18)

    toStr = f'({toAddr[:4]}-{toAddr[-4:]})'
    fromStr = f'({fromAddr[:4]}-{fromAddr[-4:]})'
    if fromAddr == topicAddr:
        fromStr = f'(me  -{fromAddr[-4:]})'
        toStr = f'(them-{toAddr[-4:]})'
        theirAddr = toAddr
    elif toAddr == topicAddr:
        toStr = f'(me  -{toAddr[-4:]})'
        fromStr = f'(them-{fromAddr[-4:]})'
        theirAddr = fromStr
    else:
        print('Error! not either to or from!')
    if value != 0:
        transactionsOut.append({
            'from': fromStr,
            'amount': value,
            'token': 'ONE',
            'to': toStr,
            'topic': 'baseTX'})

    if len(tx[Const.RECEIPT_KEY]['logs']) > 0:
        'has logs! will check if log topics are transfers.'

        for log in tx[Const.RECEIPT_KEY]['logs']:
            'For each log within each transaction'
            isTransfer = False
            tokenSym = log['address']
            value = 0
            if len(log['data']) == 66:
                try:
                    if log['data'][:4] != '0xff':
                        data = int(log['data'], 16)
                        value = data
                    else:
                        data = re.sub(r'([f])\1+', r'\1', log['data'])
                except:
                    data = log['data']
            else:
                data = 'Long Data'

            if log['address'] in HRC20Tokens:
                tokenSym = HRC20Tokens[log['address']]['symbol']
                if type(data) == float:
                    data = data / \
                        (10 ** HRC20Tokens[log['address']]['decimals'])
                    value = data
                elif type(data) == int:
                    data = data // (10 **
                                    HRC20Tokens[log['address']]['decimals'])
                    value = data
            else:
                tokenSym = tokenSym[-4:]

            myLog = 0
            theirLog = 0
            for i, topic in enumerate(log['topics']):
                if (topic[-40:]).lower() == topicAddr:
                    myLog = i
                if (topic[-40:]).lower() == theirAddr:
                    theirLog = i

            if myLog > 0:
                'Is a log for me!'

                match log['topics'][0]:
                    case '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                        isTransfer = True
                        topicName = 'Transfer'
                        fromStr = f'({log["topics"][1][-40:-36]}-{log["topics"][1][-4:]})'
                        toStr = f'({log["topics"][2][-40:-36]}-{log["topics"][2][-4:]})'

                        if myLog == 1:
                            fromStr = f'(me  -{topicAddr[-4:]})'
                        elif myLog == 2:
                            toStr = f'(me  -{topicAddr[-4:]})'
                        else:
                            print('Error, should have topic 1 or 2.')

                        if theirLog == 1:
                            fromStr = f'(them-{theirAddr[-4:]})'
                        elif theirLog == 2:
                            toStr = f'(them-{theirAddr[-4:]})'

                    case '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925':
                        topicName = 'Approval'
                    case '0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f':
                        topicName = 'Mint'
                    case '0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04':
                        topicName = 'AccruInterest'
                    case '0x71bab65ced2e5750775a0613be067df48ef06cf92a496ebf7663ae0660924954':
                        topicName = 'Harvest'
                    case '0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140':
                        topicName = 'Toekn Exchange'
                    case '0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1':
                        topicName = 'Repay Borrow'
                    case '0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80':
                        topicName = 'Borrow'
                    case '0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c':
                        topicName = 'Deposit'
                    case '0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929':
                        topicName = 'Redeem'
                    case _:
                        topicName = log['topics'][0][-4:]
                if isTransfer:
                    transactionsOut.append({
                        'from': fromStr,
                        'amount': data,
                        'token': tokenSym,
                        'to': toStr,
                        'topic': topicName})
                else:
                    unknownTxOut.append({
                        'from': fromStr,
                        'amount': data,
                        'token': tokenSym,
                        'to': toStr,
                        'topic': topicName})

    # transactionsOut.extend(unknownTxOut)
    return transactionsOut


def getHRC20Count(oneAddy) -> int:

    try:
        HRC20Counter = []
        url = Const.ENDPOINT + 'shard/0/address/' + convert_one_to_hex(
            oneAddy).lower() + '/transactions/type/erc20?offset=0&limit='+str(5000)
        response = requests.get(url)
        jsonResponse = json.loads(response.text)
        if response.status_code == 200:
            # print(f'Bucket {i}: Found {len(jsonResponse)} new transactions. Total {len(hrc20Ts)}')
            HRC20Counter.extend(jsonResponse)
        else:
            print(f'Error getting count. Status code: {response.status_code}')

        while (response.status_code == 200 and len(jsonResponse) == 5000):
            i += 1
            url = Const.ENDPOINT + 'shard/0/address/' + convert_one_to_hex(
                oneAddy).lower() + '/transactions/type/erc20?offset='+str(5000*i)+'&limit='+str(5000)
            response = requests.get(url)
            jsonResponse = json.loads(response.text)
            HRC20Counter.extend(jsonResponse)

        print(f'Expecting {len(HRC20Counter)} HRC20 transactions.')
        return len(HRC20Counter)
    except:
        return 0


def MakeFunctionList(outputFile, MetaMAskLogs):
    '''
    Description:
    BeAware:
    Inputs:
    Output:
    Notes:
    ToDo:
    '''
    with open('log.txt', 'a') as f:
        f.write(f"\nAdding Metamask functions to transactions")
    print("\n")
    print(f'Adding Metamask functions to {outputFile}')

    TxOut = {}

    if os.path.exists(outputFile):
        with open(outputFile, 'r') as f:
            TxOut = json.loads(f.read())

    # logs = list(MetaMAskLogs['metamask']['knownMethodData'].items())
    for log in MetaMAskLogs['metamask']['knownMethodData']:
        if log not in TxOut:
            if 'name' not in MetaMAskLogs['metamask']['knownMethodData'][log]:
                TxOut[log] = {"name": Const.UNDEFINEDFUNCTION}
            else:
                TxOut[log] = MetaMAskLogs['metamask']['knownMethodData'][log]
        else:
            # is in TxOut. Do not overwrite entry.
            if 'name' not in TxOut[log]:
                TxOut[log] = {"name": Const.UNDEFINEDFUNCTION}

    with open(outputFile, 'w', encoding='utf-8') as f:
        f.write(json.dumps(TxOut, ensure_ascii=False, indent=4))

    return TxOut


def getFunctionName(FunctionList, tx):
    if len(tx['input']) >= 10 and tx['input'][0:10] in FunctionList and Const.NAMEKEY in FunctionList[tx['input'][0:10]]:
        return FunctionList[tx['input'][0:10]][Const.NAMEKEY]
    elif tx['input'] in FunctionList and Const.NAMEKEY in FunctionList[tx['input']]:
        return FunctionList[tx['input']][Const.NAMEKEY]
    else:
        return Const.UNKNOWNFUNCTION


@Timer(name="Got all HRC20 tokens in {:.2f} seconds")
def writeAllTokensToFile(filePath) -> dict:
    '''
    Updates the HRC20 token list Harmony have online.

    BeAware:
        - filePath is over written.

    Input:
    {filePath} File path to overwrite HRC20 List.

    Output:
    {dict} Dictionary containing list of token information with key = token address in 0x format.

    ToDo: 
        - update log file.
    '''
    global HRC20Tokens
    print('\n')
    print('Updated Tokens to ./' + filePath)
    url = Const.ENDPOINT + 'erc20/'
    response = requests.get(url)
    processedTokens = {}
    RawTokens = json.loads(response.text)
    for token in RawTokens:
        processedTokens.update({token["address"]: token})

    with open(filePath, 'w', encoding='utf-8') as f:
        f.write(json.dumps(processedTokens, ensure_ascii=False, indent=4))

    HRC20Tokens = processedTokens
    return processedTokens


def LoadABI(filePath) -> str:
    '''
    Read ABI contracts info to string.

    BeAware:

    Input:
    {filePath} File path containing ABI information.

    Output:
    {str} String containing ABI information read from {filePath}

    ToDo: 
        - Find get method to auto compile all ABIs.
    '''
    sample_ABI = ''
    with open(filePath, 'r') as abi:
        sample_ABI += ''.join(abi.readlines())

    return sample_ABI


def printUpdate(timeStart, timeLast, updateFreq, percentage, message):
    if time.perf_counter() - timeLast > updateFreq:
        timeLast = time.perf_counter()
        if ((percentage)/(timeLast - timeStart)) == 0:
            secRem = 8000
        else:
            secRem = (100 - percentage)/((percentage)/(timeLast - timeStart))
        print(f'{percentage:.1f}% | {int(secRem)}s remaining. {message}')
        with open(Const.LOGPATH, 'a') as f:
            f.write(
                f'\n\t{percentage:.1f}% - {int(secRem)}s remaining. {message}')
        return timeLast
    return timeLast


@Timer(name='Updated JSON keys ')
def updateOutputFile(oldkey, newkey, outPath):
    print('\n')
    print(
        f'Updateding JSON keys from \'{oldkey}\' to \'{newkey}\' in \'{outPath}\'')

    TxOut = []
    if os.path.exists(outPath):
        with open(outPath, 'r') as f:
            TxOut = json.loads(f.read())
        count = 0
        for i, tx in enumerate(TxOut):
            if oldkey in tx:
                tx[newkey] = tx.pop(oldkey)
                count += 1

        with open(outPath, 'w', encoding='utf-8') as f:
            json.dump(TxOut, f, ensure_ascii=False, indent=4)
            print(f"Updated {count}/{len(TxOut)} tansactions to {outPath}")
    else:
        print(f"No file found at {outPath}")


def webScrape(ethHash, driver) -> str:
    '''
    Will assume drive is active and closed outside of this function.

    ToDo:
        - This does not catch DFK send garderner function!
    '''
    txStemSite = 'https://explorer.harmony.one/tx/'

    successXCODE = '//*[@id="scrollBody"]/div[2]/div[1]/div/div[2]/div/div/div[2]/div[1]/table/tbody/tr[1]/td/div/div/div/span'
    functionXCODE = '//*[@id="scrollBody"]/div[2]/div[1]/div/div[2]/div/div/div[2]/div[1]/table/tbody/tr[16]/td/div/div/div/div[1]/span'
    DFKsendGardener = '//*[@id="scrollBody"]/div[2]/div[1]/div/div[2]/div/div/div[2]/div[1]/table/tbody/tr[16]/td/div/div/div/div[1]'
    nullXcode = '//*[@id="scrollBody"]/div[2]/div[1]/div/div[2]/div/div/div[2]/div[1]/table/tbody/tr[16]/td/div/div/div/div/div/span'

    outputText = Const.UNKNOWNFUNCTION
    try:
        url = txStemSite+ethHash
        driver.get(url)
        wait = WebDriverWait(driver, 60, poll_frequency=1)

        #   This will check if the page loaded. (Will have success under status)
        successCode = wait.until(
            lambda d: d.find_element_by_xpath(successXCODE))

        if successCode.text == 'Success':
            try:
                functionName = driver.find_element_by_xpath(functionXCODE)
                # element = wait.until(lambda d: d.find_element_by_xpath(xCode) or d.find_element_by_xpath(nullXcode))
                outputText = functionName.text
                # print(f"{successCode.text} | {functionName.text} | {ethHash}")
            except:
                inputData = driver.find_element_by_xpath(nullXcode)
                outputText = inputData.text
                # print(f"{successCode.text} | {inputData.text} | {ethHash}")
        else:
            # print(f"No success. got : {successCode.text}")
            functionName = successCode.text
            with open('log.txt', 'a') as f:
                f.write(f"Tx {ethHash}: No success. got : {successCode.text}")
                f.write('\n')

    except:
        # print(f"Error with ethHAsh: {ethHash}")
        functionName = Const.UNKNOWNFUNCTION
        with open('log.txt', 'a') as f:
            f.write(f"Tx {ethHash}: Error, could not access XCODE")
            f.write('\n')

    return outputText

# -------------------------------------------------------------
# Utilities and support functions


def decode_tx(address, input_data, abi):
    if abi is not None:
        try:
            (contract, abi) = _get_contract(address, abi)
            func_obj, func_params = contract.decode_function_input(input_data)
            target_schema = [
                a['inputs'] for a in abi if 'name' in a and a['name'] == func_obj.fn_name][0]
            decoded_func_params = convert_to_hex(func_params, target_schema)
            return (func_obj.fn_name, json.dumps(decoded_func_params), json.dumps(target_schema))
        except:
            e = sys.exc_info()[0]
            return ('decode error', repr(e), None)
    else:
        return ('no matching abi', None, None)


def convert_one_to_hex(addr) -> str:
    """
    Given a one address, convert it to hex checksum address
    NOTE: This function is NOT thread safe due to the C function used by the bech32 library.
    Parameters
    ----------
    addr: str
                    String of address to convert, starting with one1 
    Returns
    -------
    str
                    Converted string containing hex address, now starting with 0x
    """
    if not is_valid_address(addr):
        return to_checksum_address(addr)
    hrp, data = bech32_decode(addr)
    buf = convertbits(data, 5, 8, False)
    address = '0x' + ''.join('{:02x}'.format(x) for x in buf)
    return to_checksum_address(address)


def convert_hex_to_one(addr) -> str:
    """
    Given a hex checksum address, convert it to a harmony One1 address
    NOTE: This function is NOT thread safe due to the C function used by the bech32 library.
    Parameters
    ----------
    addr: str
                    String of address to convert, starting with 0x 
    Returns
    -------
    str
                    Converted string containing one1 address, now starting with 0x
    """
    # Should validate address
    try:
        if addr[0:2] == '0x':
            addrTrimmed = addr.replace('0x', '')
            dOut = [int(addrTrimmed[i:i+2], 16)
                    for i in range(0, len(addrTrimmed), 2)]
            # Buffer.from(address.replace('0x', ''), 'hex'), 8, 5)
            addrBz = convertbits(dOut, 8, 5, False)
            if addrBz == None:
                return (None, 'Could not convert byte Buffer to 5-bit Buffer')
            return bech32_encode('one', addrBz)
        elif addr[0:4] == 'one1' and is_valid_address(addr):
            return addr
    except:
        return None
        print('ERROR CONVERTING HEX TO ONE~!')
    return None


def convertbits(data, frombits, tobits, pad=True) -> list:
    """
    General power-of-2 base conversion.
    Parameters
    ----------
    data: , frombits, tobits, pad=True
    address: str
                    String to check if valid one address
    Returns
    -------
    list
                    Is valid address
    """
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def is_valid_address(address) -> bool:
    """
    Check if given string is valid one address
    NOTE: This function is NOT thread safe due to the C function used by the bech32 library.
    Parameters
    ----------
    address: str
                    String to check if valid one address
    Returns
    -------
    bool
                    Is valid address
    """
    if not address.startswith('one1'):
        return False
    hrp, _ = bech32_decode(address)
    if not hrp:
        return False
    return True


def decode_tuple(t, target_field):
    output = dict()
    for i in range(len(t)):
        if isinstance(t[i], (bytes, bytearray)):
            # output[target_field[i]['name']] = convert_one_to_hex(t[i])
            output[target_field[i]['name']] = to_hex(t[i])
        elif isinstance(t[i], (tuple)):
            output[target_field[i]['name']] = decode_tuple(
                t[i], target_field[i]['components'])
        else:
            output[target_field[i]['name']] = t[i]
    return output


def decode_list_tuple(l, target_field):
    output = l
    for i in range(len(l)):
        output[i] = decode_tuple(l[i], target_field)
    return output


def decode_list(l):
    output = l
    for i in range(len(l)):
        if isinstance(l[i], (bytes, bytearray)):
            output[i] = to_hex(l[i])
        else:
            output[i] = l[i]
    return output


def convert_to_hex(arg, target_schema):
    """
    utility function to convert byte codes into human readable and json serializable data structures
    """
    output = dict()
    for k in arg:
        if isinstance(arg[k], (bytes, bytearray)):
            output[k] = to_hex(arg[k])
        elif isinstance(arg[k], (list)) and len(arg[k]) > 0:
            target = [
                a for a in target_schema if 'name' in a and a['name'] == k][0]
            if target['type'] == 'tuple[]':
                target_field = target['components']
                output[k] = decode_list_tuple(arg[k], target_field)
            else:
                output[k] = decode_list(arg[k])
        elif isinstance(arg[k], (tuple)):
            target_field = [a['components']
                            for a in target_schema if 'name' in a and a['name'] == k][0]
            output[k] = decode_tuple(arg[k], target_field)
        else:
            output[k] = arg[k]
    return output


@lru_cache(maxsize=None)
def _get_contract(address, abi):
    """
    This helps speed up execution of decoding across a large dataset by caching the contract object
    It assumes that we are decoding a small set, on the order of thousands, of target smart contracts
    """
    if isinstance(abi, (str)):
        abi = json.loads(abi)
    contract = w3.eth.contract(
        address=Web3.toChecksumAddress(address), abi=abi)
    print('---')
    print(contract)
    print('---')
    return (contract, abi)

# -------------------------------------------------------------
# Decoding message functions
