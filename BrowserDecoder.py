import json
import os
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime, timezone
from tkinter import *
from tkinter import filedialog, simpledialog, ttk
from tkinter.messagebox import showinfo

from pycoingecko import CoinGeckoAPI
from tabulate import tabulate

import src.HmyTx_Constants as Const
import src.HmyTx_Utils as HmyUtil
from src.lib.pyhmy.pyhmy import account, transaction, util

julianAddy1 = 'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3'
julianAddy2 = 'one1nzvl9a558tp54qw773xs6yeutkshqg3my5mksz'
julianAddy3 = 'one1vzw8vmjeplfcjf8w0fdlkt6g26et4tj462sn4n'

lucasAddy1 = '0xa8dc4998f180dfea36eb2d401746de0efe5cf03c'
lucasAddy2 = '0xf9358cc0b2a2b8f20da1edd5d385e2d59a5370e3'
lucasAddy3 = '0xb24f92f4517176f24f9e8167e8aefdcd2ebff5b8'

metaMaskLogPath = f'TokenInfo/MetaMask State Logs.json'
metamaskFunctions = 'TokenInfo/MetaMaskFunctions.json'

outputDirectory = f'./TransactionHistory/'

needsFixing = {'0x18cbafe5': 'Not getting wONE. look in input string',
               '0x4a25d94a': 'Not getting wONE. look in input string',
               '0x02751cec': 'remove liquidity but ONE not found. input not correct amount, see logs...',
               '0x2e1a7d4d': 'Withdrawal topic. 0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65',
               '0xae169a50': 'Claim has locked transfers, must receive difference...',
               '0x4a517a55': 'Swap and redeeme only jewel from... why?',

               '0x1cf5f07f': 'Withdraw of jewelX but no to/from address. check HRC20!',
               '0x17357892': 'Mint and swap, unsure whats happeneing, JEWEL n something...',

               '0xbcf64e05': 'wagmi burn ',
               '0xa0e3d1a0': 'wagmi burn ',

               '0x23b872dd': 'transfer with 4 inputs. small amoutn unknown...',
               '0x303e6aa4': 'Not sure what is converted. multiple tokens small ammounts...',
               '0x8dbdbe6d': 'WAGMI deposits of stable coins AND DFK working',
               '0xb6b55f25': 'deposit of ONE, think working, simple transfer',
               '0x690e7c09': 'DFK hero open? sell? no small transfers'
               }


class MainWindow(tk.Tk):

    filetypes = (
        ('json files', '*.json'),
        ('All files', '*.*'))

    textMessage = ''
    isLoading = False

    def __init__(self):
        # self.master = master
        super().__init__()
        self.geometry("1080x640")
        self.title("Harmony Transaction Exporter")
        # self.pack(fill=BOTH, expand=True)

        self.frame = tk.Frame(self)
        self.frame.pack()

        # Account details
        self.oneAddress = tk.StringVar()
        self.oneAddress.set('Enter harmony address here.')
        self.addrEntry = ttk.Entry(
            self.frame, textvariable=self.oneAddress, width=35)
        self.addrEntry.grid(column=0, row=1, columnspan=1, padx=5, pady=5)
        self.addrEntry.bind('<KeyRelease>', self.CheckAddress)

        self.oneAddrStr = tk.StringVar()
        self.oneAddrStr.set('No address detected.')
        self.oneAddreassLabel = ttk.Label(
            self.frame, textvariable=self.oneAddrStr)
        self.oneAddreassLabel.grid(
            column=0, row=2, columnspan=2, padx=5, pady=5)

        self.AccButton = ttk.Button(
            self.frame, text="Load Account", command=self.DownloadData)
        self.AccButton.grid(column=1, row=1, columnspan=1, padx=5, pady=5)
        self.AccButton.state(["disabled"])   # Disable the button.

        # Progressbar
        self.progressBarText = tk.StringVar()
        self.progressBar1 = ttk.Progressbar(
            self.frame,
            orient='horizontal',
            mode='indeterminate',
            length=280
        )
        self.progressBar2 = ttk.Progressbar(
            self.frame,
            orient='horizontal',
            mode='determinate',
            length=280,
            maximum=100
        )
        self.progressBar1.grid(column=0, row=3, columnspan=2, padx=10, pady=5)
        self.progressBar2.grid(column=0, row=4, columnspan=2, padx=10, pady=5)
        self.progressBar2.grid_forget()
        self.value_label = ttk.Label(
            self.frame, textvariable=self.progressBarText)
        self.value_label.grid(column=0, row=5, columnspan=2)

        self.ProcessButton = ttk.Button(
            self.frame, text="Organise Transactions", command=self.processData)
        self.ProcessButton.grid(
            column=0, row=4, columnspan=1, ipadx=10, ipady=10)
        self.ProcessButton.grid_forget()

        self.PrintButton = ttk.Button(
            self.frame, text="Print Transactions", command=self.printData)
        self.PrintButton.grid(
            column=1, row=4, columnspan=1, ipadx=10, ipady=10)
        self.PrintButton.grid_forget()

        # Text Widget
        self.scrollx = tk.Scrollbar(self.frame, orient=tk.HORIZONTAL)
        self.scrollx.grid(column=0, row=7, columnspan=2, ipadx=350)
        self.text = tk.Text(self.frame, wrap=tk.NONE,
                            undo=True, xscrollcommand=self.scrollx.set)
        self.text.grid(column=0, row=6, columnspan=2, ipadx=100, padx=10)
        self.scrollx.config(command=self.text.xview)

    def addToText(self, message):
        with open(Const.LOGPATH, 'a') as f:
            f.write(message+'\n')
        print(message)
        self.textMessage += message
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', self.textMessage+'\n')

    def CheckAddress(self, event) -> bool:
        if len(self.oneAddress.get()) == 42 and (HmyUtil.is_valid_address(self.oneAddress.get()) or (self.oneAddress.get()[:2] == '0x' and HmyUtil.convert_hex_to_one(self.oneAddress.get()) != None)):
            harmaddr = HmyUtil.convert_hex_to_one(self.oneAddress.get())
            self.oneAddrStr.set(
                'Got address:\n\t - '+harmaddr+'\n\t - '+(HmyUtil.convert_one_to_hex(harmaddr)).lower())
            self.AccButton.state(["!disabled"])  # Enable the button.
            return True
        else:
            self.oneAddrStr.set('No address detected.')
            self.AccButton.state(["disabled"])   # Disable the button.
            return False

    def DownloadData(self):
        if self.CheckAddress(None) and not self.isLoading:
            self.progressBar1.start()
            self.progressBar2['value'] = 0
            self.progressBarText.set('Downloading Data...')
            self.isLoading = True
            self.transactionsController = transactionDownloader(
                self.oneAddress.get(), self)

        else:
            print("Ya fucked")

    def processData(self):
        self.addToText(
            '\n------------------------------------------------\nNow Processing!\n')
        self.transactionsController.ManualFunctionLabeler()

        self.addToText('All done!')

    def printData(self):
        self.addToText(
            '\n------------------------------------------------\nNow Printing!\n')
        self.transactionsController.GetDFKrewards()

        self.addToText('All done!')
        showinfo("All printed", "Printed all transactions to CSV.")


class FunctionSelector(tk.Toplevel):

    fnList = {}
    fnCode = ''
    fnTxs = {}
    oneAddress = ''
    allTransactions = {}
    addrGroupedTransactions = {}

    isShowingAll = True
    hasDirtyLists = False
    haveLabeledAll = False

    # The lists for combo boxes
    txFnList = []
    uniqueAddr = []
    txList = []

    def __init__(self, TransactionList, oneAddress):
        super().__init__()

        self.fnList = HmyUtil.getFunctions()

        self.allTransactions = TransactionList
        self.oneAddress = oneAddress

        self.txFnList = []
        for code in self.allTransactions:
            if code in self.fnList:
                self.txFnList.append(f"{self.fnList[code]['name']} | {code}")
            else:
                self.txFnList.append(f'Unknown | {code}')
                self.fnList[code] = {"name": Const.FUNC_UNDEFINED}
        # self.txFnList = list(TransactionList.keys())

        self.fnCode = self.txFnList[0].split(' | ', 1)[1]
        self.fnTxs = self.allTransactions[self.fnCode]

        # List
        self.txList = self.digestTxs(self.fnTxs, oneAddress)

        self.title('Main Window')

        self.frame = tk.Frame(self)
        self.frame.pack()

        self.functionLabelStr = StringVar()
        self.addressLabelStr = StringVar()
        self.transactionLabelStr = StringVar()

        self.functionLabelStr.set('No Label')
        self.addressLabelStr.set('No Label')
        self.transactionLabelStr.set('No Label')

        # -- row 0 -------- New label setter ---------
        ttk.Label(self.frame, text="Select Label:").grid(
            column=0, row=0, columnspan=1, padx=5, pady=5)

        self.labelSelector = ttk.Combobox(
            self.frame, values=self.fnList['labels'], width=20)
        self.labelSelector.grid(
            column=1, row=0, columnspan=1, padx=5, pady=5)
        self.labelSelector.set(self.labelSelector['values'][0])

        self.newLabel = tk.StringVar()
        self.newLabel.set('Enter new label.')
        self.labelEntry = ttk.Entry(
            self.frame, textvariable=self.newLabel, width=20).grid(
                column=2, row=0, columnspan=1, padx=5, pady=5)
        ttk.Button(self.frame,
                   text='Add to list',
                   command=self.addLabelToList).grid(
                       column=3, row=0, columnspan=1, padx=5, pady=5)

        # -- row 1 -------- Function selection ---------
        ttk.Label(self.frame, text="Select Function:").grid(
            column=0, row=1, columnspan=1, padx=5, pady=5)

        # Combobox
        self.FunctionSelector = ttk.Combobox(
            self.frame, values=self.txFnList, width=20)
        self.FunctionSelector.grid(
            column=1, row=1, columnspan=1, padx=5, pady=5)
        self.FunctionSelector.set(self.FunctionSelector['values'][0])
        self.FunctionSelector.bind('<<ComboboxSelected>>', self.updateFunction)
        # button
        ttk.Button(self.frame,
                   text='Set to Function',
                   command=self.setFunctionLabel).grid(
                       column=2, row=1, columnspan=1, padx=5, pady=5)
        self.FuncLabel = ttk.Label(
            self.frame, textvariable=self.functionLabelStr)
        self.FuncLabel.grid(column=3, row=1, columnspan=1, padx=5, pady=5)

        # -- row 2 -------- Address selection ---------
        ttk.Label(self.frame, text="Their Address:").grid(
            column=0, row=2, columnspan=1, padx=5, pady=5)
        # Combobox
        self.AddrSelector = ttk.Combobox(
            self.frame, values=self.uniqueAddr, width=20)
        self.AddrSelector.grid(
            column=1, row=2, columnspan=1, padx=5, pady=5)
        self.AddrSelector.set(self.uniqueAddr[0])
        self.AddrSelector.bind('<<ComboboxSelected>>', self.updateAddr)
        # button
        ttk.Button(self.frame,
                   text='Set to Address',
                   command=self.setAddressLabel).grid(
                       column=2, row=2, columnspan=1, padx=5, pady=5)
        self.AddrLabel = ttk.Label(
            self.frame, textvariable=self.addressLabelStr)
        self.AddrLabel.grid(column=3, row=2, columnspan=1, padx=5, pady=5)

        # -- row 3 -------- Transaction selection ---------
        ttk.Label(self.frame, text="Sample Transaction:").grid(
            column=0, row=3, columnspan=1, padx=5, pady=5)
        # Combobox
        self.TxSelector = ttk.Combobox(
            self.frame, values=self.txList, width=20)
        self.TxSelector.grid(
            column=1, row=3, columnspan=1, padx=5, pady=5)
        self.TxSelector.set(self.txList[0])
        self.TxSelector.bind('<<ComboboxSelected>>', self.updateTxHash)
        # button
        ttk.Button(self.frame,
                   text='Set to Transaction',
                   command=self.setTransactionLabel).grid(
                       column=2, row=3, columnspan=1, padx=5, pady=5)
        self.TxLabel = ttk.Label(
            self.frame, textvariable=self.transactionLabelStr)
        self.TxLabel.grid(column=3, row=3, columnspan=1, padx=5, pady=5)

        # -- row 4 -------- Button  ---------
        ttk.Button(self.frame,
                   text='Label From Default',
                   command=self.LabelFromDefault).grid(
                       column=0, row=4, columnspan=1, padx=5, pady=5)
        self.b_showOnlyNoLabels = ttk.Button(self.frame,
                                             text='Show Unlabeled Only',
                                             command=self.ShowUnlabeled)
        self.b_showOnlyNoLabels.grid(
            column=1, row=4, columnspan=1, padx=5, pady=5)

        self.b_applyLabels = ttk.Button(self.frame,
                                        text='Apply Labels to Txs',
                                        command=self.ApplyLabelToTransactions)
        self.b_applyLabels.grid(
            column=1, row=4, columnspan=1, padx=5, pady=5)
        self.b_applyLabels.grid_forget()

        self.b_showAll = ttk.Button(self.frame,
                                    text='Show All',
                                    command=self.ShowAll)
        self.b_showAll.grid(column=1, row=4, columnspan=1, padx=5, pady=5)
        self.b_showAll.grid_forget()
        ttk.Button(self.frame,
                   text='Save Function Labels',
                   command=self.SaveFunctionListFile).grid(
                       column=2, row=4, columnspan=1, padx=5, pady=5)
        ttk.Button(self.frame,
                   text='View Tx Online',
                   command=self.openTransactionSite).grid(
                       column=3, row=4, columnspan=1, padx=5, pady=5)

        # -- row 5 -------- Text Widget ---------
        self.scrollx = tk.Scrollbar(self.frame, orient=tk.HORIZONTAL)
        self.scrollx.grid(column=0, row=6, columnspan=4, ipadx=350)
        self.text = tk.Text(self.frame, wrap=tk.NONE,
                            undo=True, xscrollcommand=self.scrollx.set)
        self.text.grid(column=0, row=5, columnspan=4, ipadx=100, padx=10)
        self.scrollx.config(command=self.text.xview)
        self.ShowUnlabeled()
        self.ShowAll()
        self.updateAddr(None)

    def ApplyLabelToTransactions(self):
        print('Applying labels to all transactions!')
        txPath = Const.TXOUTPATH + self.oneAddress + '.json'
        if os.path.exists(txPath):
            with open(txPath, 'r') as f:
                rawTXs = json.loads(f.read())
            count = 0
            txCount = 0
            if Const.TRANSACTIONS_KEY in rawTXs:
                for txHash in rawTXs[Const.TRANSACTIONS_KEY]:
                    tx = rawTXs[Const.TRANSACTIONS_KEY][txHash]
                    txCount += 1
                    label = HmyUtil.getLabel(tx, self.oneAddress)

                    # add label if its got a name.
                    if label != None:
                        count += 1

                        if Const.T_FUNCTION_KEY in tx:
                            tx[Const.T_FUNCTION_KEY][Const.TF_FUNCLABEL] = label
                        else:
                            tx[Const.T_FUNCTION_KEY] = {
                                Const.TF_FUNCLABEL: label}

                    # add trade info
                    tr = HmyUtil.getTransferInfo(
                        tx, self.oneAddress)  # This gets label from tx...
                    if Const.T_FUNCTION_KEY in tx:
                        tx[Const.T_FUNCTION_KEY].update(tr)
                    else:
                        tx[Const.T_FUNCTION_KEY] = tr

            with open(txPath, 'w', encoding='utf-8') as f:
                json.dump(rawTXs, f, ensure_ascii=False, indent=4)

            alldoneMSG = showinfo("Labeling Complete",
                                  f'Labeled {count}/{txCount} transactions.\nWill now close manual labeler')
            self.destroy()

    def LabelFromDefault(self):
        print("Label from default value!")
        for code in self.allTransactions:
            'if code in function list, has defult but not this oneAddress'
            if code in self.fnList and Const.F_DEFAULT_KEY in self.fnList[code] and self.oneAddress not in self.fnList[code]:
                self.fnList[code][self.oneAddress] = self.fnList[code][Const.F_DEFAULT_KEY]
            else:
                print(f'{code} not found')
        self.SaveFunctionListFile()

    def ShowUnlabeled(self):
        print("Showing Unlabeled Only!")
        self.isShowingAll = False
        self.hasDirtyLists = True
        self.b_showOnlyNoLabels.grid_forget()
        self.b_applyLabels.grid_forget()
        self.b_showAll.grid(column=1, row=4, columnspan=1, padx=5, pady=5)
        self.fixShownLabels()

    def ShowAll(self):
        print("Showing all transactions!")
        self.isShowingAll = True
        self.hasDirtyLists = True
        self.b_showAll.grid_forget()
        self.fixShownLabels()
        if self.haveLabeledAll:
            self.b_showOnlyNoLabels.grid_forget()
            self.b_applyLabels.grid(
                column=1, row=4, columnspan=1, padx=5, pady=5)
        else:
            self.b_applyLabels.grid_forget()
            self.b_showOnlyNoLabels.grid(
                column=1, row=4, columnspan=1, padx=5, pady=5)

    def digestTxs(self, Transactions, oneAddress):
        self.addrGroupedTransactions = {}
        for i, hash in enumerate(Transactions):
            if 'status' in Transactions[hash][Const.T_RECEIPT_KEY] and Transactions[hash][Const.T_RECEIPT_KEY]['status'] != 0:
                try:
                    fromAddr = Transactions[hash][Const.T_TX_KEY]['from']
                    toAddr = Transactions[hash][Const.T_TX_KEY]['to']
                    if oneAddress == fromAddr:
                        'one address is from'
                        if toAddr not in self.addrGroupedTransactions:
                            'add new address and tx hash.'
                            self.addrGroupedTransactions[toAddr] = [hash]
                        else:
                            'add tx hash to existing address'
                            self.addrGroupedTransactions[toAddr].append(hash)
                    elif oneAddress == toAddr:
                        'one address in to'
                        if fromAddr not in self.addrGroupedTransactions:
                            'add new address and tx hash.'
                            self.addrGroupedTransactions[fromAddr] = [hash]
                        else:
                            'add tx hash to existing address'
                            self.addrGroupedTransactions[fromAddr].append(hash)
                    else:
                        (f'Error, oneAddress not found to or from. {hash}')
                        if toAddr not in self.addrGroupedTransactions:
                            'add new address and tx hash.'
                            self.addrGroupedTransactions[toAddr] = [hash]
                        else:
                            'add tx hash to existing address'
                            self.addrGroupedTransactions[toAddr].append(hash)
                except:
                    print(Transactions[hash])
                    break
            else:
                'Transaction did not get function or receipt for TX: {hash}'
        self.uniqueAddr = list(self.addrGroupedTransactions.keys())
        return self.addrGroupedTransactions[self.uniqueAddr[0]]

    def openTransactionSite(self):
        site = f'https://explorer.harmony.one/tx/{self.TxSelector.get()}'
        webbrowser.open(site, new=0)
        print(f'Opened {site}')

    def addLabelToList(self):
        print('function loaded!')
        if self.newLabel.get() not in self.fnList['labels']:
            self.fnList['labels'].append(self.newLabel.get())
            self.labelSelector['values'] = self.fnList['labels']
            self.labelSelector.set(self.labelSelector['values'][-1])
            # self.updateFunctionListFile()
        else:
            print('Already in list you numpty')

    def SaveFunctionListFile(self):
        print("Updating functions list!")
        self.fnList = HmyUtil.updateFunctions(self.fnList)
        showinfo("Update Complete", f'Function list updated!')

    def fixShownLabels(self):
        if self.hasDirtyLists:
            if not self.isShowingAll:
                print('Cleaning Lists')
                self.hasDirtyLists = False

                for func in self.FunctionSelector['values']:
                    if func.split(' | ', 1)[1] in self.fnList and self.oneAddress in self.fnList[func.split(' | ', 1)[1]]:
                        if self.fnList[func.split(' | ', 1)[1]][self.oneAddress]['functionLabel'] != None:
                            options = list(self.FunctionSelector['values'])
                            options.remove(func)
                            self.FunctionSelector['values'] = options
                            # print(f'Removed {func}')

                for func in self.FunctionSelector['values']:

                    self.FunctionSelector.set(func)
                    self.updateFunction(None)

                    funcCode = func.split(' | ', 1)[1]
                    for Addr in self.AddrSelector['values']:
                        if funcCode in self.fnList and self.oneAddress in self.fnList[funcCode]:
                            if Addr in self.fnList[funcCode][self.oneAddress]['addressLabels']:
                                options = list(self.AddrSelector['values'])
                                options.remove(Addr)
                                self.AddrSelector['values'] = options
                                # print(f'Removed {Addr}')
                    if len(list(self.AddrSelector['values'])) == 0:
                        options = list(self.FunctionSelector['values'])
                        options.remove(func)
                        self.FunctionSelector['values'] = options
                        # print(f'Removed {func}')
                    else:
                        break

                if len(list(self.FunctionSelector['values'])) == 0:
                    print('All functions labeled!!')
                    self.haveLabeledAll = True
                    self.FunctionSelector['values'] = []
                    self.AddrSelector['values'] = []
                    self.TxSelector['values'] = []
                    self.FunctionSelector.set('')
                    self.AddrSelector.set('')
                    self.TxSelector.set('')
                    self.updateDisplay(None)
                else:
                    """if self.FunctionSelector.get() not in self.FunctionSelector['values']:
                        self.FunctionSelector.set(
                            self.FunctionSelector['values'][0])

                    self.updateFunction(None)"""

                    if self.AddrSelector.get() not in self.AddrSelector['values']:
                        self.AddrSelector.set(self.AddrSelector['values'][0])

                    """if len(list(self.AddrSelector['values'])) == 0:
                        options = list(self.FunctionSelector['values'])
                        options.remove(self.FunctionSelector.get())
                        if len(options) != 0:
                            self.FunctionSelector['values'] = options"""

                    self.updateAddr(None)

                    for tx in self.TxSelector['values']:
                        if funcCode in self.fnList and self.oneAddress in self.fnList[funcCode]:
                            if tx in self.fnList[funcCode][self.oneAddress]['transactionLabels']:
                                options = list(self.TxSelector['values'])
                                options.remove(tx)
                                self.TxSelector['values'] = options
                                print(f'Removed {tx}')

                    if self.TxSelector.get() not in self.TxSelector['values']:
                        self.TxSelector.set(self.TxSelector['values'][0])

            else:
                self.hasDirtyLists = False
                self.FunctionSelector['values'] = self.txFnList
                self.FunctionSelector.set(self.FunctionSelector['values'][0])
                self.updateFunction(None)
        else:
            'Lists not dirty'

    def updateFunction(self, event):
        self.fnCode = self.FunctionSelector.get().split(' | ', 1)[1]
        self.fnTxs = self.allTransactions[self.fnCode]

        self.txList = self.digestTxs(self.fnTxs, self.oneAddress)

        self.AddrSelector['values'] = self.uniqueAddr
        self.AddrSelector.set(self.AddrSelector['values'][0])
        self.updateAddr(None)

    def updateAddr(self, event):
        self.TxSelector['values'] = self.addrGroupedTransactions[self.AddrSelector.get()]
        self.TxSelector.set(self.TxSelector['values'][0])
        self.updateDisplay(self.TxSelector.get())

    def updateTxHash(self, event):
        self.updateDisplay(self.TxSelector.get())

    def updateDisplay(self, transactionHash):
        displayText = f'My Harmony address: {self.oneAddress}\n\n'
        if transactionHash in self.fnTxs:
            selectedTx = self.fnTxs[transactionHash]
            displayText += f'Function: {self.fnList[self.fnCode]["name"]} | {self.fnCode}\n'
            '''
            Date:   24-04-14 02:04:14
            from:   one1sdff (me)
            to:     one1asgr (them)
                    from (me  -1jd3) to (1sG3-19k4) - 204.214 ONE
                    from (them-1jd3) to (1sG3-19k4) - 204.214 ONE
            '''
            baseInfo = HmyUtil.getBaseInfoDisplay(selectedTx, self.oneAddress)
            displayText += f'\nDate:\t{baseInfo["time"]}'
            displayText += f'\nfrom:\t{baseInfo["from"]}'
            displayText += f'\nto:\t{baseInfo["to"]}'
            (knownInfo, UnknownInfo) = HmyUtil.getTransferInfoDisplay(
                selectedTx, self.oneAddress)
            for txInfo in knownInfo:
                displayText += f'\n  {txInfo["topic"]}\tfrom {txInfo["from"]} to {txInfo["to"]} - {txInfo["amount"]} {txInfo["token"]}'
            displayText += "\n----------------------------------------------------------------------\n"
            for txInfo in UnknownInfo:
                displayText += f'\n  {txInfo["topic"]}\tfrom {txInfo["from"]} to {txInfo["to"]} - {txInfo["amount"]} {txInfo["token"]}'

        if self.haveLabeledAll:
            displayText = '----------------------------------------------------------------------\n\t\tHAVE LABELED ALL TRANSACTIONS\n----------------------------------------------------------------------\n' + displayText
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', displayText)
        self.updateFunctionLabelDisplays()

    def updateFunctionLabelDisplays(self):
        self.fixShownLabels()
        if self.haveLabeledAll and not self.isShowingAll:
            self.functionLabelStr.set('No Tx')
            self.addressLabelStr.set('No Tx')
            self.transactionLabelStr.set('No Tx')
        else:
            self.functionLabelStr.set('No Label')
            self.addressLabelStr.set('No Label')
            self.transactionLabelStr.set('No Label')

            if self.oneAddress in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
                labels = self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                    1]][self.oneAddress]
                if labels['functionLabel'] is not None:
                    self.functionLabelStr.set(labels['functionLabel'])
                if self.AddrSelector.get() in labels['addressLabels']:
                    self.addressLabelStr.set(
                        labels['addressLabels'][self.AddrSelector.get()])
                if self.TxSelector.get() in labels['transactionLabels']:
                    self.transactionLabelStr.set(
                        labels['transactionLabels'][self.TxSelector.get()])
            elif 'default' in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
                labels = self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                    1]]['default']
                if labels['functionLabel'] is not None:
                    self.functionLabelStr.set('(default) ' +
                                              labels['functionLabel'])
                if self.AddrSelector.get() in labels['addressLabels']:
                    self.addressLabelStr.set('(default) ' +
                                             labels['addressLabels'][self.AddrSelector.get()])
                if self.TxSelector.get() in labels['transactionLabels']:
                    self.transactionLabelStr.set('(default) ' +
                                                 labels['transactionLabels'][self.TxSelector.get()])

    def setFunctionLabel(self):
        if self.FunctionSelector.get().split(' | ', 1)[1] not in self.fnList:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]] = {
                'name': Const.FUNC_UNKNOWN}

        if 'default' not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]['default'] = {
                'functionLabel': self.labelSelector.get(), 'addressLabels': {}, 'transactionLabels': {}}
        else:
            self.fnList[self.FunctionSelector.get().split(
                ' | ', 1)[1]]['default']['functionLabel'] = self.labelSelector.get()

        if self.oneAddress not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]][self.oneAddress] = {
                'functionLabel': self.labelSelector.get(), 'addressLabels': {}, 'transactionLabels': {}}
        else:
            self.fnList[self.FunctionSelector.get().split(
                ' | ', 1)[1]][self.oneAddress]['functionLabel'] = self.labelSelector.get()
        if not self.isShowingAll:
            self.hasDirtyLists = True
        self.updateFunctionLabelDisplays()

    def setAddressLabel(self):
        if self.FunctionSelector.get().split(' | ', 1)[1] not in self.fnList:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]] = {
                'name': Const.FUNC_UNKNOWN}

        if 'default' not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]['default'] = {
                'functionLabel': None, 'addressLabels': {self.AddrSelector.get(): self.labelSelector.get()}, 'transactionLabels': {}}
        else:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                1]]['default']['addressLabels'][self.AddrSelector.get()] = self.labelSelector.get()

        if self.oneAddress not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]][self.oneAddress] = {
                'functionLabel': None, 'addressLabels': {self.AddrSelector.get(): self.labelSelector.get()}, 'transactionLabels': {}}
        else:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                1]][self.oneAddress]['addressLabels'][self.AddrSelector.get()] = self.labelSelector.get()
        if not self.isShowingAll:
            self.hasDirtyLists = True
        self.updateFunctionLabelDisplays()

    def setTransactionLabel(self):
        if self.FunctionSelector.get().split(' | ', 1)[1] not in self.fnList:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]] = {
                'name': Const.FUNC_UNKNOWN}

        if 'default' not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]['default'] = {
                'functionLabel': None, 'addressLabels': {}, 'transactionLabels': {self.TxSelector.get(): self.labelSelector.get()}}
        else:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                1]]['default']['transactionLabels'][self.TxSelector.get()] = self.labelSelector.get()

        if self.oneAddress not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]][self.oneAddress] = {
                'functionLabel': None, 'addressLabels': {}, 'transactionLabels': {self.TxSelector.get(): self.labelSelector.get()}}
        else:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                1]][self.oneAddress]['transactionLabels'][self.TxSelector.get()] = self.labelSelector.get()
        if not self.isShowingAll:
            self.hasDirtyLists = True
        self.updateFunctionLabelDisplays()


class transactionDownloader:

    outputDirectory = f'./TransactionHistory/'

    GUI = None

    functionList = {}
    HRC20List = {}
    accountDetails = {}
    haveFile = False

    oneAddress = ''

    def __init__(self, oneAddress, GUI):
        self.GUI = GUI
        self.oneAddress = oneAddress
        if self.oneAddress[:2] == '0x':
            self.oneAddress = HmyUtil.convert_hex_to_one(oneAddress)

        self.start()

    def refresh(self):
        self.GUI.update()
        self.GUI.after(100, self.refresh)

    def start(self):
        self.refresh()
        threading.Thread(target=self.setupJSON).start()

    def setupJSON(self):
        self.functionList = HmyUtil.getFunctions()

        self.GUI.addToText(
            '------------------------------------------------\nDownloading all HRC20 tokens from harmony database.\n')
        self.HRC20List = HmyUtil.writeAllTokensToFile(Const.HRC20LISTPATH)

        self.GUI.addToText(
            f'\n------------------------------------------------\nDownloading all transactions for {self.oneAddress}.\n')
        self.accountDetails = self.SetupTransactions()

        self.GUI.addToText(
            f'\n------------------------------------------------\nDownloading receipts for each transaction within {self.oneAddress}.\n')

        self.accountDetails = self.DecodeTransactions(
            accountDetails=self.accountDetails, functionList=self.functionList, ABIs=None)

        self.haveFile = True
        self.GUI.progressBar1.stop()
        self.GUI.progressBar2['value'] = 100
        self.GUI.progressBarText.set('All loaded and decoded!')
        self.GUI.isLoading = False
        self.GUI.progressBar2.grid_forget()
        self.GUI.ProcessButton.grid(
            column=0, row=4, columnspan=1, ipadx=10, ipady=10)
        self.GUI.PrintButton.grid(
            column=1, row=4, columnspan=1, ipadx=10, ipady=10)

    def SetupTransactions(self) -> dict:
        '''
        Description:
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''

        self.outputJSONFile = f'{self.outputDirectory}{self.oneAddress}.json'

        accountInfoOut = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                accountInfoOut = json.loads(f.read())

        '''
        Transactions format,
        {
            counts:{Tx,HRC20,Function,Receipt,Decode,Web},
            transactions:{'ethHash':{Tx,HRC20,Function,Receipt,Decode,Web}
        }
        '''

        onfileTXCount = 0
        onfileHRC20Count = 0
        fileTxs = {}
        if Const.COUNTS_KEY in accountInfoOut:
            onfileTXCount = accountInfoOut[Const.COUNTS_KEY][Const.T_TX_KEY]
            onfileHRC20Count = accountInfoOut[Const.COUNTS_KEY][Const.T_HRC20_KEY]
            fileTxs = accountInfoOut[Const.TRANSACTIONS_KEY]
        else:
            accountInfoOut = {Const.COUNTS_KEY: {
                Const.T_TX_KEY: 0, Const.T_HRC20_KEY: 0, Const.T_FUNCTION_KEY: [0, 0, 0], Const.T_RECEIPT_KEY: [0, 0, 0], Const.T_DECODED_KEY: [0, 0, 0], Const.T_WEB_KEY: [0, 0, 0]}}

        nAttempts = 10
        pageSize = 100
        expectedTXs = 1
        expectedHRC20s = 1
        count = 0
        noOnline = True
        while count < nAttempts and noOnline:
            try:
                expectedTXs = (account.get_transactions_count(
                    self.oneAddress, tx_type='ALL', endpoint=Const.MAINNET0))
                expectedHRC20s = HmyUtil.getHRC20Count(self.oneAddress)
                noOnline = False
            except BaseException as err:
                self.GUI.addToText(
                    f"Writing Log Unexpected {err=}, {type(err)=}\n\t{err.with_traceback}")

        onFileHash = list(fileTxs.keys())

        remainingTxCount = expectedTXs - onfileTXCount
        remainingHRC20Count = expectedHRC20s - onfileHRC20Count

        '''
        GUI.addToText(f'\n\t\t| On File\t| Online\t| To Add')
        GUI.addToText(
            f'\nTransactions:\t\t| {onfileTXCount}\t| {expectedTXs}\t| {remainingTxCount}')
        GUI.addToText(
            f'\nHRC20s:\t\t| {onfileHRC20Count}\t| {expectedHRC20s}\t| {remainingHRC20Count}\n')
        '''

        txCount = 0
        newTxCount = 0
        skippedTxCount = 0
        duplicateCount = 0

        HRC20Count = 0
        newHRC20Count = 0
        skipptedHRC20Count = 0

        if remainingTxCount == 0 or noOnline:
            'Have all transactions downloaded! can skip'
            skippedTxCount = onfileTXCount
            onFileHash = []
            # self.GUI.addToText(
            #    f"\nHave all transactions on file.\n\t {skippedTxCount + newTxCount}/{expectedTXs} transactions.\n")
        else:
            self.GUI.progressBar2.grid(
                column=0, row=4, columnspan=2, padx=10, pady=5)
            countsTAble = [['Transactions', onfileTXCount, expectedTXs, remainingTxCount], [
                'HRC20 Tokens', onfileHRC20Count, expectedHRC20s, remainingHRC20Count]]

            self.GUI.addToText('\nNew transactions found!\n\n' + tabulate(countsTAble, headers=[
                '', 'On File', 'Online', 'To Add'])+'\n')

            pageCount = 0
            maxpages = expectedTXs//pageSize + 1
            timeLast = time.perf_counter()
            lastAmount = 0
            while pageCount < maxpages:
                if newTxCount == remainingTxCount:
                    skippedTxCount = onfileTXCount
                    onFileHash = []
                    break
                try:
                    if txCount <= expectedTXs:
                        newTxs = account.get_transaction_history(
                            self.oneAddress, page=pageCount, page_size=pageSize, include_full_tx=True, tx_type='ALL', order='DESC', endpoint=Const.MAINNET0)

                        for i, tx in enumerate(newTxs):
                            if tx['ethHash'] not in fileTxs:
                                fileTxs[tx['ethHash']] = {Const.T_TX_KEY: tx}
                                newTxCount += 1
                            elif tx['ethHash'] in onFileHash:
                                'Transaction in file. remove from fileList'
                                onFileHash.remove(tx['ethHash'])
                                skippedTxCount += 1
                            else:
                                'Transaction in file and  duplicate list'
                                duplicateCount += 1

                            (timeLast, lastAmount) = self.simpleLoadingUpdate(timeLast, lastAmount, expectedTXs, txCount+i,
                                                                              f"Page {pageCount}/{maxpages}: Downloaded {(skippedTxCount+newTxCount)}/{expectedTXs} transactions. Added {newTxCount}/{remainingTxCount} transactions.")

                        txCount += len(newTxs)
                    else:
                        'tried to add all transactions'

                    pageCount += 1

                except BaseException as err:
                    self.GUI.addToText(
                        f"Error while getting transactions. Writing Log Unexpected {err=}, {type(err)=}")

            # self.GUI.addToText(
            #    f"\nTransactions:\n\tDownloaded {txCount}/{expectedTXs} transactions.\n\tAdded {newTxCount}/{remainingTxCount} transactions.\n\tTotal {skippedTxCount + newTxCount}/{expectedTXs} transactions.\nAll Transactions Done!\n")
        """
        if duplicateCount-len(onFileHash) != 0:
            self.GUI.addToText(
                f'{duplicateCount} transactions not received from Harmony API.\n{len(onFileHash)} transactions on file and not received.\n{duplicateCount-len(onFileHash)} remaining online. Re-run to download all transactions.')
        else:
            self.GUI.addToText(
                f'All files downloaded!\n{duplicateCount} transactions not received from Harmony API.\n{len(onFileHash)} transactions on file and not received.')
        """

        if remainingHRC20Count == 0:
            'Have all transactions downloaded! can skip'
            skipptedHRC20Count = onfileHRC20Count
            # self.GUI.addToText(
            #    f"\nHave all HRC20 transactions on file.\n\t {skipptedHRC20Count + newHRC20Count}/{expectedHRC20s} transactions.\n")

        else:
            pageCount = 0
            maxpages = expectedHRC20s//pageSize + 1

            timeLast = time.perf_counter()
            lastAmount = 0
            while pageCount < maxpages:
                try:
                    if HRC20Count < expectedHRC20s:
                        newHRC20 = HmyUtil.getHRC20(
                            oneAddy=self.oneAddress, pageIndex=pageCount, pageSize=pageSize)

                        HRC20Count += len(newHRC20)

                        for i, hrc20 in enumerate(newHRC20):
                            if remainingHRC20Count != 0:

                                """(timeStart, percentageStart, timeLast, percentageLast, timeStep) = self.UpdateLoadingBar(
                                    timeStart,
                                    percentageStart,
                                    timeLast,
                                    percentageLast, timeStep,
                                    100.0 * newHRC20Count / remainingHRC20Count,
                                    f"\nPage {pageCount}/{maxpages}: Downloaded {HRC20Count}/{expectedHRC20s} HRC20 tokens. Added {newHRC20Count}/{remainingHRC20Count} HRC20 tokens. Total {len(fileTxs)} transactions.",
                                    GUI)"""

                            if hrc20['transactionHash'] not in fileTxs:
                                tempTX = transaction.get_transaction_by_hash(
                                    hrc20["transactionHash"], endpoint=Const.MAINNET0)
                                fileTxs[hrc20['transactionHash']] = {}
                                fileTxs[hrc20['transactionHash']
                                        ][Const.T_TX_KEY] = tempTX
                                fileTxs[hrc20['transactionHash']
                                        ][Const.T_HRC20_KEY] = hrc20
                                newHRC20Count += 1
                            elif Const.T_HRC20_KEY not in fileTxs[hrc20['transactionHash']]:
                                fileTxs[hrc20['transactionHash']
                                        ][Const.T_HRC20_KEY] = hrc20
                                newHRC20Count += 1
                            else:
                                'HRC20 in file.'
                                skipptedHRC20Count += 1

                            (timeLast, lastAmount) = self.simpleLoadingUpdate(timeLast, lastAmount, expectedHRC20s, (skipptedHRC20Count+newHRC20Count),
                                                                              f"\nPage {pageCount}/{maxpages}: Downloaded {(skipptedHRC20Count+newHRC20Count)}/{expectedHRC20s} HRC20 tokens. Added {newHRC20Count}/{remainingHRC20Count} HRC20 tokens.")
                    else:
                        'tried to add all HRC20 transactions'

                    pageCount += 1

                    if newHRC20Count == expectedHRC20s:
                        'Have downloaded enough!'
                        skipptedHRC20Count = onfileHRC20Count
                        break

                except BaseException as err:
                    self.GUI.addToText(
                        f"Writing HRC20 Log Unexpected {err=}, {type(err)=}")

            # self.GUI.addToText(
            #    f"\nHRC20 transactions:\n\tDownloaded {HRC20Count}/{expectedHRC20s} HRC20 tokens.\n\tAdded {newHRC20Count}/{remainingHRC20Count} HRC20 tokens.\n\tTotal {skipptedHRC20Count + newHRC20Count}/{expectedHRC20s} HRC20 tokens.\nAll HRC20s Done!\n")

        accountInfoOut[Const.COUNTS_KEY][Const.T_TX_KEY] = (
            len(onFileHash) + skippedTxCount+newTxCount)
        accountInfoOut[Const.COUNTS_KEY][Const.T_HRC20_KEY] = (
            skipptedHRC20Count+newHRC20Count)
        accountInfoOut[Const.TRANSACTIONS_KEY] = fileTxs

        with open(self.outputJSONFile, 'w', encoding='utf-8') as f:
            json.dump(accountInfoOut, f, ensure_ascii=False, indent=4)

        headers = ['', 'On File', 'Online', 'New',
                   'Added', 'Skipped', 'Remaining', 'Total']
        counterDisplay = [['Transactions', onfileTXCount, expectedTXs, remainingTxCount, newTxCount, len(onFileHash) + skippedTxCount, duplicateCount-len(onFileHash), len(onFileHash) + skippedTxCount+newTxCount],
                          ['HRC20 Txs', onfileHRC20Count, expectedHRC20s, remainingHRC20Count, newHRC20Count, skipptedHRC20Count, expectedHRC20s-(skipptedHRC20Count+newHRC20Count), skipptedHRC20Count+newHRC20Count]]
        self.GUI.addToText(
            '\n'+tabulate(counterDisplay, headers=headers)+'\n')
        """
        self.GUI.addToText(
            f"\n{len(fileTxs)} Transactions saved to file.")
        self.GUI.addToText(
            f"\n\t{skippedTxCount+newTxCount+len(onFileHash)} transactions.")
        self.GUI.addToText(
            f"\n\t{skipptedHRC20Count+newHRC20Count} HRC20 transactions.")
        """

        return accountInfoOut

    def simpleLoadingUpdate(self, timeLast, lastAmount, totalAmount, amount, message):
        updateFreq = 2
        percentage = 100*amount/totalAmount

        if (amount-lastAmount) > 0 and time.perf_counter() - timeLast > updateFreq:
            secPereAmount = (time.perf_counter()-timeLast)/(amount-lastAmount)
            sec = (totalAmount-amount)*secPereAmount
            minRem = sec//60
            hrRem = sec//3600
            secRem = sec - minRem*60
            lastAmount = amount
            timeLast = time.perf_counter()
            self.GUI.progressBar2['value'] = percentage
            self.GUI.progressBarText.set(
                f'{percentage:.1f}% \t {hrRem:.0f}hrs {minRem:.0f}min {secRem:.0f}sec remaining.\n{message}')
            print(f'{percentage:.1f}% {message}')
        return (timeLast, lastAmount)

    def ManualFunctionLabeler(self):
        '''
        Description:
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        hexAddr = HmyUtil.convert_one_to_hex(self.oneAddress)
        topicAddr = hexAddr[2:].lower()
        allTransactions = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                allTransactions = json.loads(f.read())

        orderedFunctions = self.getfunctionSorted(
            allTransactions=allTransactions)

        func = FunctionSelector(orderedFunctions, self.oneAddress)
        # func.grab_set()
        print('DONE!!!')

    def updateTokenList(self):
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
        allTransactions = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                allTransactions = json.loads(f.read())

        tokenBook = {}
        addressPath = f'./TokenInfo/CoinGeckoContracts.json'

        if os.path.exists(addressPath):
            with open(addressPath, 'r') as f:
                tokenBook = json.loads(f.read())

        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONS_KEY]):
            tx = allTransactions[Const.TRANSACTIONS_KEY][txHash]

            if 'Receipt' in tx and 'status' in tx['Receipt'] and tx['Receipt']['status'] != 0:
                #  transactionInfo = {'time','name','code','gas','to','from','trades','unknownTrades','label'}
                #       Trade keys = {'from','to','sentAmount','sentToken','receivedAmount','receivedToken','topic','label'}
                tr = HmyUtil.getTransferInfo(tx, self.oneAddress)

                for trade in tr[Const.TF_TRADES]:
                    'add to token list'
                    tokenName = trade[Const.TFT_RECTOKEN]
                    if trade[Const.TFT_SENTTOKEN] != '':
                        tokenName = trade[Const.TFT_SENTTOKEN]

                    if trade[Const.TFT_TCONT] not in tokenBook:
                        tokenBook[trade[Const.TFT_TCONT]] = {
                            Const.CG_CHAINID: "harmony-shard-0",
                            Const.CG_CONTRACT: trade[Const.TFT_TCONT],
                            Const.CG_NAME: tokenName,
                            Const.CG_ISONLINE: True}

        with open(addressPath, 'w', encoding='utf-8') as f:
            json.dump(tokenBook, f, ensure_ascii=False, indent=4)

    def GetDFKrewards(self):
        '''
        Description:
            outputs list of reward (income) events for DFK.
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        self.updateTokenList()

        hexAddr = HmyUtil.convert_one_to_hex(self.oneAddress)
        topicAddr = hexAddr[2:].lower()
        allTransactions = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                allTransactions = json.loads(f.read())

        csvOut = 'Date,Amount,Coin,Timestamp,Matched Timestamp,US Price,US Value,AUD Price, AUD Value,Label,Contract,Their Addr,TxHash\n'

        PathBase = './HistoryData/'
        historyTokenPaths = os.listdir(PathBase)

        marketData = {}
        for Path in historyTokenPaths:
            with open(PathBase+Path, 'r') as f:
                marketData.update({Path[:-5]: json.loads(f.read())})

        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONS_KEY]):
            tx = allTransactions[Const.TRANSACTIONS_KEY][txHash]

            if 'Receipt' in tx and 'status' in tx['Receipt'] and tx['Receipt']['status'] != 0:
                #  transactionInfo = {'time','name','code','gas','to','from','trades','unknownTrades','label'}
                #       Trade keys = {'from','to','sentAmount','sentToken','receivedAmount','receivedToken','topic','label'}
                tr = HmyUtil.getTransferInfo(tx, self.oneAddress)

                if tr[Const.TF_FUNCLABEL] == 'LP Swap' or tr[Const.TF_FUNCLABEL] == 'Claim':

                    rewards = {}
                    for trade in tr[Const.TF_TRADES]:
                        'get the name, get the amount'

                        price = self.getPrice(
                            marketData, trade[Const.TFT_TCONT], tx[Const.T_TX_KEY]['timestamp']*1000)

                        name = trade[Const.TFT_RECTOKEN]
                        amount = trade[Const.TFT_RECAMOUNT]
                        if trade[Const.TFT_SENTTOKEN] != '':
                            name = trade[Const.TFT_SENTTOKEN]
                            amount = -trade[Const.TFT_SENTAMOOUNT]
                        if 'LP' not in name:
                            if name not in rewards:
                                rewards.update({name: {
                                                'amount': amount,
                                                Const.TFT_TCONT: trade[Const.TFT_TCONT],
                                                'price': price}})
                            else:
                                rewards[name]['amount'] += amount
                    for name in rewards:
                        'Date,Amount,Coin,Timestamp,Matched Timestamp,US Price,US Value,AUD Price, AUD Value,Label,Contract,Their Addr,TxHash\n'
                        csvOut += f"{tr[Const.TF_TIME]},{rewards[name]['amount']},{name},{tx[Const.T_TX_KEY]['timestamp']},{rewards[name]['price'][2]},{rewards[name]['price'][0]},{rewards[name]['amount']*rewards[name]['price'][0]},{rewards[name]['price'][1]},{rewards[name]['amount']*rewards[name]['price'][1]},{tr[Const.TF_FUNCLABEL]},{rewards[name][Const.TFT_TCONT]},{tr[Const.TF_THEIR]},{txHash}\n"

        with open(f'./CSV Outputs/testRewards_{self.oneAddress}.csv', 'w') as f:
            f.write(csvOut)

    def getPrice(self, historyData, contract, timestamp):
        if contract in historyData:
            matchedTime = 0
            for i, timest in enumerate(historyData[contract]['FineUSD']['prices']):
                if timestamp < timest[0]:
                    matchedTime = historyData[contract]['FineUSD']['prices'][i][0]
                    USprice = historyData[contract]['FineUSD']['prices'][i][1]
                    AUprice = historyData[contract]['FineAUD']['prices'][i][1]
                    break
            return (USprice, AUprice, matchedTime)
        else:
            return(0, 0, timestamp)

    def CleanFunctions(self) -> dict:
        '''
        Description:
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        hexAddr = HmyUtil.convert_one_to_hex(self.oneAddress)
        topicAddr = hexAddr[2:].lower()

        allTransactions = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                allTransactions = json.loads(f.read())

        cleanedTXs = {}

        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONS_KEY]):
            tx = allTransactions[Const.TRANSACTIONS_KEY][txHash]

            if Const.T_RECEIPT_KEY in tx and 'status' in tx[Const.T_RECEIPT_KEY] and tx[Const.T_RECEIPT_KEY]['status'] != 0:
                #  transactionInfo = {'time','name','code','gas','to','from','label','trades'[],'unknownTrades'[]}
                #       Trade keys = {'from','to','sentAmount','sentToken','receivedAmount','receivedToken','topic'}
                tr = HmyUtil.getTransferInfo(tx, self.oneAddress)
                if Const.T_FUNCTION_KEY in tx:
                    tx[Const.T_FUNCTION_KEY].update(tr)
                match tr['label']:
                    case "reward":
                        ''
                    case "liquidity in" | "liquidity out":
                        ''
                    case "DFK":
                        ''
                    case  "Transfer":
                        ''
                    case  "WAGMI Transfer":
                        ''
                    case  "DFK Stake":
                        ''
                    case  "Trade":
                        ''
                    case  "LP Swap":
                        ''
                    case  "WAGMI":
                        ''
                    case _:
                        ''

                for trade in tr['trades']:
                    if trade['sentToken'] != '':
                        'is sent'
                    elif trade['receivedToken'] != '':
                        'is received'

    def PrintLabeled(self):
        '''
        Description:
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        hexAddr = HmyUtil.convert_one_to_hex(self.oneAddress)
        topicAddr = hexAddr[2:].lower()
        allTransactions = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                allTransactions = json.loads(f.read())

        cleanedTXs = {}

        unknownCsvOut = dfkOut = csvOut = 'Date,Sent Amount,Sent Currency,Received Amount,Received Currency,Fee Amount,Fee Currency,Net Worth Amount,Net Worth Currency,Label,Description,Code,Their Addr,TxHash\n'

        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONS_KEY]):
            tx = allTransactions[Const.TRANSACTIONS_KEY][txHash]

            if 'Receipt' in tx and 'status' in tx['Receipt'] and tx['Receipt']['status'] != 0:
                #  transactionInfo = {'time','name','code','gas','to','from','trades','unknownTrades'}
                #       Trade keys = {'from','to','sentAmount','sentToken','receivedAmount','receivedToken','topic','label'}
                tr = HmyUtil.getTransferInfo(tx, self.oneAddress)

                for trade in tr['trades']:
                    if trade['label'] == 'DFK':
                        dfkOut += f"{tr['time']},{trade['sentAmount']},{trade['sentToken']},{trade['receivedAmount']},{trade['receivedToken']},{tr['gas']},ONE,,,{trade['label']},{trade['topic']},{tr[Const.TF_FUNCCODE]},{trade[Const.TFT_THEIR]},{tx[Const.T_TX_KEY]['ethHash']}\n"
                    else:
                        csvOut += f"{tr['time']},{trade['sentAmount']},{trade['sentToken']},{trade['receivedAmount']},{trade['receivedToken']},{tr['gas']},ONE,,,{trade['label']},{trade['topic']},{tr[Const.TF_FUNCCODE]},{trade[Const.TFT_THEIR]},{tx[Const.T_TX_KEY]['ethHash']}\n"

                for trade in tr['unknownTrades']:
                    unknownCsvOut += f"{tr['time']},{trade['sentAmount']},{trade['sentToken']},{trade['receivedAmount']},{trade['receivedToken']},{tr['gas']},ONE,,,{trade['label']},{trade['topic']},{tr[Const.TF_FUNCCODE]},{trade[Const.TFT_THEIR]},{tx[Const.T_TX_KEY]['ethHash']}\n"

        with open(f'./CSV Outputs/test_{self.oneAddress}.csv', 'w') as f:
            f.write(csvOut)

        with open(f'./CSV Outputs/test_{self.oneAddress}_DFK.csv', 'w') as f:
            f.write(dfkOut)

        with open(f'./CSV Outputs/test_{self.oneAddress}_unkown.csv', 'w') as f:
            f.write(unknownCsvOut)

    def RAWPrintTransfersToCSV(self):
        '''
        Description:
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        hexAddr = HmyUtil.convert_one_to_hex(self.oneAddress)
        topicAddr = hexAddr[2:].lower()
        allTransactions = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                allTransactions = json.loads(f.read())

        unknownCsvOut = csvOut = 'date,function,code,type,token,amount,direction,gas,ethHash'

        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONS_KEY]):
            tx = allTransactions[Const.TRANSACTIONS_KEY][txHash]
            timestamp = datetime.fromtimestamp(tx[Const.T_TX_KEY]['timestamp'])
            timestr = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            typeName = tx[Const.T_FUNCTION_KEY]['function']
            typeCode = tx[Const.T_FUNCTION_KEY]['code']
            gasFee = tx[Const.T_TX_KEY]['gasPrice'] * \
                tx[Const.T_RECEIPT_KEY]['gasUsed'] / (10 ** 18)

            value = tx[Const.T_TX_KEY]['value'] / (10 ** 18)
            fromInfo = []
            toInfo = []
            unknownInfo = []
            if value != 0:
                if tx[Const.T_TX_KEY]['from'] == self.oneAddress:
                    fromInfo.append({'amount': value,
                                     'token': 'ONE', 'topic': 'baseTX'})
                elif tx[Const.T_TX_KEY]['to'] == self.oneAddress:
                    toInfo.append({'amount': value,
                                   'token': 'ONE', 'topic': 'baseTX'})

            if len(tx[Const.T_RECEIPT_KEY]['logs']) > 0:
                for log in tx[Const.T_RECEIPT_KEY]['logs']:
                    'For each log within each transaction'
                    tokenSym = log['address']
                    data = log['data']
                    if log['address'] in self.HRC20List:
                        tokenSym = self.HRC20List[log['address']]['symbol']
                        try:
                            if data[:4] != '0xff':
                                data = int(log['data'], 16) / \
                                    (10 **
                                     self.HRC20List[log['address']]['decimals'])
                        except:
                            data = log['data']
                    myLog = 0
                    for i, topic in enumerate(log['topics']):
                        if (topic[-40:]).lower() == topicAddr:
                            myLog = i
                    if myLog > 0:
                        'Is a log for me!'
                        match log['topics'][0]:
                            case '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                                'Transfer'
                                if myLog == 1:
                                    fromInfo.append(
                                        {'amount': data, 'token': tokenSym, 'topic': 'Transfer'})
                                elif myLog == 2:
                                    toInfo.append(
                                        {'amount': data, 'token': tokenSym, 'topic': 'Transfer'})
                                else:
                                    print('Error, should have topic 1 or 2.')
                                    unknownInfo.append(
                                        {'amount': data, 'token': tokenSym, 'topic': 'Transfer'})
                            case '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925':
                                'Approval'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Approval'})
                            case '0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f':
                                'Mint'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Mint'})
                            case '0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04':
                                'AccruInterest'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'AccruInterest'})
                            case '0x71bab65ced2e5750775a0613be067df48ef06cf92a496ebf7663ae0660924954':
                                'Harvest'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Harvest'})
                            case '0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140':
                                'Toekn Exchange'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Toekn Exchange'})
                            case '0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1':
                                'Repay Borrow'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Repay Borrow'})
                            case '0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80':
                                'Borrow'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Borrow'})
                            case '0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c':
                                'Deposit'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Deposit'})
                            case '0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929':
                                'Redeem'
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': 'Redeem'})
                            case _:
                                unknownInfo.append(
                                    {'amount': data, 'token': tokenSym, 'topic': log['topics'][0]})

            for t in fromInfo:
                csvOut += f'\n{timestr},{typeName},{typeCode},{t["topic"]},{t["token"]},{t["amount"]},from,{gasFee},{tx[Const.T_TX_KEY]["ethHash"]}'
            for t in toInfo:
                csvOut += f'\n{timestr},{typeName},{typeCode},{t["topic"]},{t["token"]},{t["amount"]},to,{gasFee},{tx[Const.T_TX_KEY]["ethHash"]}'
            for t in unknownInfo:
                unknownCsvOut += f'\n{timestr},{typeName},{typeCode},{t["topic"]},{t["token"]},{t["amount"]},unknown,{gasFee},{tx[Const.T_TX_KEY]["ethHash"]}'

        with open(f'./CSV Outputs/test_{self.oneAddress}.csv', 'w') as f:
            f.write(csvOut)
        with open(f'./CSV Outputs/test_{self.oneAddress}_unkown.csv', 'w') as f:
            f.write(unknownCsvOut)

    def getfunctionSorted(self, allTransactions) -> dict:
        transactionsOut = {}
        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONS_KEY]):
            tx = allTransactions[Const.TRANSACTIONS_KEY][txHash]
            if 'Receipt' in tx and 'status' in tx['Receipt'] and tx['Receipt']['status'] != 0:
                typeCode = tx[Const.T_FUNCTION_KEY]['code']
                if typeCode not in transactionsOut:
                    transactionsOut[typeCode] = {txHash: tx}
                else:
                    transactionsOut[typeCode][txHash] = tx
        return transactionsOut

    def DecodeTransactions(self, accountDetails, functionList, ABIs) -> dict:
        '''
        Description:
        BeAware:
        Inputs:
        Outputs:
        Notes:
        ToDo:
        '''
        accountOut = {}
        if os.path.exists(self.outputJSONFile):
            with open(self.outputJSONFile, 'r') as f:
                accountOut = json.loads(f.read())
        '''
        Transactions format,
        {
            address:{
                counts:{Tx,HRC20,Function,Receipt,Decode,Web},
                transactions:{'ethHash':{counts,Tx,HRC20,Function,Receipt,Decode,Web}
                }
        }
        '''
        #   Counters are an array [decoded,skipped,unknown]

        # This is when decoding website doesnt work. Not really used atm.
        maxAttempts = 15

        timeLast = time.perf_counter()
        lastAmount = 0
        '''[New,Skipped,Unknown]'''
        counters = {Const.T_RECEIPT_KEY: [0, 0, 0],
                    Const.T_DECODED_KEY: [0, 0, 0],
                    Const.T_FUNCTION_KEY: [0, 0, 0],
                    Const.T_WEB_KEY: [0, 0, 0]}
        hasNew = False
        for i, (hash) in enumerate(accountDetails[Const.TRANSACTIONS_KEY]):
            txInfo = accountDetails[Const.TRANSACTIONS_KEY][hash]
            # Per transaction
            willUpdateTx = {}
            if Const.TRANSACTIONS_KEY in accountOut and hash in accountOut[Const.TRANSACTIONS_KEY]:
                'The item is in TxOut'
                if Const.COUNTS_KEY not in accountOut[Const.TRANSACTIONS_KEY][hash]:
                    accountOut[Const.TRANSACTIONS_KEY][hash][Const.COUNTS_KEY] = {
                        Const.T_RECEIPT_KEY: 0, Const.T_DECODED_KEY: 0, Const.T_FUNCTION_KEY: 0, Const.T_WEB_KEY: 0}
            # if the ethHash is not in 'TxOut' (previousely compleated) then add web info
                for (decodeKey) in counters:
                    countValues = counters[decodeKey]
                    willUpdateTx[decodeKey] = False
                    if decodeKey in accountOut[Const.TRANSACTIONS_KEY][hash]:
                        'has decoded info'
                        if Const.FUNC_NOVALUE in accountOut[Const.TRANSACTIONS_KEY][hash][decodeKey]:
                            'There is no value'
                            accountOut[Const.TRANSACTIONS_KEY][hash][decodeKey][Const.FUNC_NOVALUE] += 1
                            if accountOut[Const.TRANSACTIONS_KEY][hash][decodeKey][Const.FUNC_NOVALUE] < maxAttempts:
                                willUpdateTx[decodeKey] = True
                            elif 'function' in accountOut[Const.TRANSACTIONS_KEY][hash][decodeKey] and Const.FUNC_ERROR == accountOut[Const.TRANSACTIONS_KEY][hash][decodeKey]['function']:
                                willUpdateTx[decodeKey] = True
                                # print('We got an error! will fix..')
                            else:
                                countValues[2] += 1

                        elif Const.FUNC_UNKNOWN in accountOut[Const.TRANSACTIONS_KEY][hash][decodeKey]:
                            countValues[2] += 1
                        else:
                            'Has previous entry'
                            countValues[1] += 1
                    else:
                        'no receipt'
                        willUpdateTx[decodeKey] = True
            else:
                'The item is not in accountOut'
                willUpdateTx = {
                    Const.T_RECEIPT_KEY: True, Const.T_DECODED_KEY: True, Const.T_FUNCTION_KEY: True, Const.T_WEB_KEY: True}
                accountOut[Const.TRANSACTIONS_KEY][hash] = txInfo

            for (deKey) in willUpdateTx:
                willUpdate = willUpdateTx[deKey]
                if willUpdate:
                    hasNew = True
                    if len(accountOut[Const.TRANSACTIONS_KEY][hash][Const.T_TX_KEY]['input']) >= 10:
                        functionCode = accountOut[Const.TRANSACTIONS_KEY][hash][Const.T_TX_KEY]['input'][0:10]
                    else:
                        functionCode = accountOut[Const.TRANSACTIONS_KEY][hash][Const.T_TX_KEY]['input']
                    match deKey:
                        case Const.T_RECEIPT_KEY:
                            'will update receipt'
                            try:
                                recpt = transaction.get_transaction_receipt(
                                    txInfo[Const.T_TX_KEY]['ethHash'].lower(), Const.MAINNET0)
                                counters[deKey][0] += 1
                            except BaseException as err:
                                recpt = {
                                    Const.FUNC_NOVALUE: maxAttempts, 'function': Const.FUNC_ERROR, 'data': f'Unexpected {err=}, {type(err)=}'}
                                counters[deKey][2] += 1

                            accountOut[Const.TRANSACTIONS_KEY][hash][deKey] = recpt
                        case Const.T_DECODED_KEY:
                            'decode vairable'
                            if ABIs == None:
                                accountOut[Const.TRANSACTIONS_KEY][hash][deKey] = {
                                    Const.FUNC_UNKNOWN: maxAttempts, "function": Const.FUNC_UNKNOWN, 'code': functionCode}
                                counters[deKey][2] += 1
                            else:
                                try:
                                    for tempABI in ABIs:
                                        decoded = HmyUtil.decode_tx(
                                            HmyUtil.convert_one_to_hex(txInfo[Const.T_TX_KEY]['to']), txInfo[Const.T_TX_KEY]['input'], tempABI)

                                        if decoded[2] is not None:
                                            accountOut[Const.TRANSACTIONS_KEY][hash][deKey] = {
                                                "function": decoded[0], "data": json.loads(decoded[1])}
                                            counters[deKey][0] += 1
                                            break
                                    if decoded[2] is None:
                                        accountOut[Const.TRANSACTIONS_KEY][hash][deKey] = {
                                            Const.FUNC_NOVALUE: maxAttempts, 'function': Const.FUNC_NOVALUE}
                                        counters[deKey][2] += 1

                                except BaseException as err:
                                    accountOut[Const.TRANSACTIONS_KEY][hash][deKey] = {
                                        Const.FUNC_NOVALUE: maxAttempts, 'function': Const.FUNC_ERROR, 'data': f'Unexpected {err=}, {type(err)=}'}
                                    counters[deKey][2] += 1
                        case Const.T_FUNCTION_KEY:
                            'add function'
                            functionName = HmyUtil.getFunctionName(
                                functionList, accountOut[Const.TRANSACTIONS_KEY][hash][Const.T_TX_KEY])
                            if(functionName != Const.FUNC_UNKNOWN):
                                "Decoded function"
                                counters[deKey][0] += 1
                            else:
                                "Unknown function"
                                counters[deKey][2] += 1
                            accountOut[Const.TRANSACTIONS_KEY][hash][deKey] = {
                                "function": functionName, 'code': functionCode}
                        case Const.T_WEB_KEY:
                            'add web'
                            accountOut[Const.TRANSACTIONS_KEY][hash][deKey] = {
                                Const.FUNC_UNKNOWN: maxAttempts, "function": Const.FUNC_UNKNOWN, 'code': functionCode}
                            counters[deKey][2] += 1
                        case _:
                            print(f'Error, No catch for key {deKey}')
            'Updated all '

            '''timerlast = HmyUtil.printUpdate(timerstart, timerlast, 3, 100*i/len(accountDetails[oneAddy][Const.TRANSACTIONSKEY]),
                                            f"Tx {i}/{len(accountDetails[oneAddy][Const.TRANSACTIONSKEY])}: {counters}")'''
            counterDisplay = []
            for key in counters:
                accountOut[Const.COUNTS_KEY][key] = counters[key]
                counterDisplay.append(
                    [key, *counters[key], sum(counters[key])])
            if hasNew and i % 250 == 0:
                hasNew = False
                with open(self.outputJSONFile, 'w', encoding='utf-8') as f:
                    json.dump(accountOut, f, ensure_ascii=False, indent=4)

            (timeLast, lastAmount) = self.simpleLoadingUpdate(timeLast, lastAmount, len(accountDetails[Const.TRANSACTIONS_KEY]), i,
                                                              f"Tx {i}/{len(accountDetails[Const.TRANSACTIONS_KEY])}")
        counterDisplay = []
        for key in counters:
            accountOut[Const.COUNTS_KEY][key] = counters[key]
            counterDisplay.append([key, *counters[key], sum(counters[key])])

        self.GUI.addToText(
            '\n'+tabulate(counterDisplay, headers=['', 'New', 'Skipped', 'Unknown', 'Total'])+'\n')

        with open(self.outputJSONFile, 'w', encoding='utf-8') as f:
            json.dump(accountOut, f, ensure_ascii=False, indent=4)
            self.GUI.addToText(
                f"\n\nSaved {len(accountOut[Const.TRANSACTIONS_KEY])} transactions to {self.outputJSONFile}\n")

        return accountOut


def getCoinGeckoHistory():
    cg = CoinGeckoAPI()
    tokenBook = {}

    timestampNow = int(time.time())
    timestamp = datetime(2021, 1, 1).replace(
        tzinfo=timezone.utc).timestamp()
    timestampStart = int(timestamp)

    # Const.TXOUTPATH + f'TokenContracts_{oneAddress}.json'

    if os.path.exists(Const.CG_CONTRACTPATH):
        with open(Const.CG_CONTRACTPATH, 'r') as f:
            tokenBook = json.loads(f.read())

    for contract in tokenBook:
        try:
            coinBase = f'./HistoryData/{contract}'
            coinPath = coinBase + '.json'
            hasInAPI = True
            if Const.CG_ISONLINE not in tokenBook[contract]:
                print(
                    f'Updating {tokenBook[contract][Const.CG_NAME]} : {contract}')
                print('No data for contract. Will make new.')
                tokenBook[contract] = {
                    Const.CG_CHAINID: "harmony-shard-0",
                    Const.CG_CONTRACT: contract,
                    Const.CG_NAME: tokenBook[contract],
                    Const.CG_ISONLINE: hasInAPI}

            if Const.CG_ISONLINE not in tokenBook[contract] or (Const.CG_ISONLINE in tokenBook[contract] and tokenBook[contract][Const.CG_ISONLINE]):
                'Check api to update info.'
                print(
                    f'Updating {tokenBook[contract][Const.CG_NAME]} : {contract}')
                if Const.CG_ID in tokenBook[contract]:
                    "use the gecko id not id/contract info."
                    if(not os.path.exists(coinPath)):
                        print('Have not downloaded info. Will do it now.')

                        time.sleep(2)
                        coins = (cg.get_coin_by_id(
                            id=tokenBook[contract][Const.CG_ID]))

                        time.sleep(2)
                        AllhistoryDataUS = cg.get_coin_market_chart_range_by_id(
                            tokenBook[contract][Const.CG_ID], 'usd', str(timestampStart), str(timestampNow))

                        time.sleep(2)
                        AllhistoryDataAU = cg.get_coin_market_chart_range_by_id(
                            tokenBook[contract][Const.CG_ID],  'aud', str(timestampStart), str(timestampNow))

                        tsFin = timestampNow
                        tsStart = timestampNow - 89*24*60*60

                        time.sleep(2)
                        FinehistoryDataUS = cg.get_coin_market_chart_range_by_id(
                            tokenBook[contract][Const.CG_ID],  'usd', str(tsStart), str(tsFin))

                        time.sleep(2)
                        FinehistoryDataAU = cg.get_coin_market_chart_range_by_id(
                            tokenBook[contract][Const.CG_ID],  'aud', str(tsStart), str(tsFin))

                        tsFin = tsStart
                        tsStart = tsFin - 89*24*60*60

                        while tsStart > timestampStart:
                            time.sleep(2)
                            FinehistoryDataUS_new = cg.get_coin_market_chart_range_by_id(
                                tokenBook[contract][Const.CG_ID],  'usd', str(tsStart), str(tsFin))

                            FinehistoryDataUS["prices"].extend(
                                FinehistoryDataUS_new["prices"])
                            FinehistoryDataUS["market_caps"].extend(
                                FinehistoryDataUS_new["market_caps"])
                            FinehistoryDataUS["total_volumes"].extend(
                                FinehistoryDataUS_new["total_volumes"])

                            time.sleep(2)
                            FinehistoryDataAU_new = cg.get_coin_market_chart_range_by_id(
                                tokenBook[contract][Const.CG_ID],  'aud', str(tsStart), str(tsFin))

                            FinehistoryDataAU["prices"].extend(
                                FinehistoryDataAU_new["prices"])
                            FinehistoryDataAU["market_caps"].extend(
                                FinehistoryDataAU_new["market_caps"])
                            FinehistoryDataAU["total_volumes"].extend(
                                FinehistoryDataAU_new["total_volumes"])

                            tsFin = tsStart
                            tsStart = tsFin - 89*24*60*60

                        FinehistoryDataUS["prices"] = sorted(
                            FinehistoryDataUS["prices"])
                        FinehistoryDataUS["market_caps"] = sorted(
                            FinehistoryDataUS["market_caps"])
                        FinehistoryDataUS["total_volumes"] = sorted(
                            FinehistoryDataUS["total_volumes"])

                        FinehistoryDataAU["prices"] = sorted(
                            FinehistoryDataAU["prices"])
                        FinehistoryDataAU["market_caps"] = sorted(
                            FinehistoryDataAU["market_caps"])
                        FinehistoryDataAU["total_volumes"] = sorted(
                            FinehistoryDataAU["total_volumes"])

                        coinsInfo = {
                            Const.C_INFO: coins,
                            Const.C_COARSE_USD: AllhistoryDataUS,
                            Const.C_COARSE_AUD: AllhistoryDataAU,
                            Const.C_FINE_USD: FinehistoryDataUS,
                            Const.C_FINE_AUD: FinehistoryDataAU}

                        with open(coinPath, 'w') as f:
                            json.dump(coinsInfo, f,
                                      ensure_ascii=False, indent=4)
                else:
                    'use id/contract info'
                    if(not os.path.exists(coinPath)):
                        print('Have not downloaded info. Will do it now.')

                        time.sleep(2)
                        coins = (cg.get_coin_info_from_contract_address_by_id(
                            id=tokenBook[contract][Const.CG_CHAINID], contract_address=tokenBook[contract][Const.CG_CONTRACT]))

                        time.sleep(2)
                        AllhistoryDataUS = cg.get_coin_market_chart_range_from_contract_address_by_id(
                            tokenBook[contract][Const.CG_CHAINID], tokenBook[contract][Const.CG_CONTRACT], 'usd', str(timestampStart), str(timestampNow))

                        time.sleep(2)
                        AllhistoryDataAU = cg.get_coin_market_chart_range_from_contract_address_by_id(
                            tokenBook[contract][Const.CG_CHAINID], tokenBook[contract][Const.CG_CONTRACT], 'aud', str(timestampStart), str(timestampNow))

                        tsFin = timestampNow
                        tsStart = timestampNow - 89*24*60*60

                        time.sleep(2)
                        FinehistoryDataUS = cg.get_coin_market_chart_range_from_contract_address_by_id(
                            tokenBook[contract][Const.CG_CHAINID], tokenBook[contract][Const.CG_CONTRACT], 'usd', str(tsStart), str(tsFin))

                        time.sleep(2)
                        FinehistoryDataAU = cg.get_coin_market_chart_range_from_contract_address_by_id(
                            tokenBook[contract][Const.CG_CHAINID], tokenBook[contract][Const.CG_CONTRACT], 'aud', str(tsStart), str(tsFin))

                        tsFin = tsStart
                        tsStart = tsFin - 89*24*60*60

                        while tsStart > timestampStart:
                            time.sleep(2)
                            FinehistoryDataUS_new = cg.get_coin_market_chart_range_from_contract_address_by_id(
                                tokenBook[contract][Const.CG_CHAINID], tokenBook[contract][Const.CG_CONTRACT], 'usd', str(tsStart), str(tsFin))

                            FinehistoryDataUS["prices"].extend(
                                FinehistoryDataUS_new["prices"])
                            FinehistoryDataUS["market_caps"].extend(
                                FinehistoryDataUS_new["market_caps"])
                            FinehistoryDataUS["total_volumes"].extend(
                                FinehistoryDataUS_new["total_volumes"])

                            time.sleep(2)
                            FinehistoryDataAU_new = cg.get_coin_market_chart_range_from_contract_address_by_id(
                                tokenBook[contract][Const.CG_CHAINID], tokenBook[contract][Const.CG_CONTRACT], 'aud', str(tsStart), str(tsFin))

                            FinehistoryDataAU["prices"].extend(
                                FinehistoryDataAU_new["prices"])
                            FinehistoryDataAU["market_caps"].extend(
                                FinehistoryDataAU_new["market_caps"])
                            FinehistoryDataAU["total_volumes"].extend(
                                FinehistoryDataAU_new["total_volumes"])

                            tsFin = tsStart
                            tsStart = tsFin - 89*24*60*60

                        FinehistoryDataUS["prices"] = sorted(
                            FinehistoryDataUS["prices"])
                        FinehistoryDataUS["market_caps"] = sorted(
                            FinehistoryDataUS["market_caps"])
                        FinehistoryDataUS["total_volumes"] = sorted(
                            FinehistoryDataUS["total_volumes"])

                        FinehistoryDataAU["prices"] = sorted(
                            FinehistoryDataAU["prices"])
                        FinehistoryDataAU["market_caps"] = sorted(
                            FinehistoryDataAU["market_caps"])
                        FinehistoryDataAU["total_volumes"] = sorted(
                            FinehistoryDataAU["total_volumes"])

                        coinsInfo = {
                            Const.C_INFO: coins,
                            Const.C_COARSE_USD: AllhistoryDataUS,
                            Const.C_COARSE_AUD: AllhistoryDataAU,
                            Const.C_FINE_USD: FinehistoryDataUS,
                            Const.C_FINE_AUD: FinehistoryDataAU}

                        with open(coinPath, 'w') as f:
                            json.dump(coinsInfo, f,
                                      ensure_ascii=False, indent=4)
            else:
                (f'{contract} not in CoinGecko')

        except Exception as e:
            if e.__context__ is not None and '429' in e.__str__():
                print('Too many request!')
                time.sleep(2)
            elif '404' in e.__context__.__str__():
                print('Could not find in CoinGecko API')
                if tokenBook[contract][Const.CG_ISONLINE]:
                    tokenBook[contract][Const.CG_ISONLINE] = False
            else:
                print('Type" ', sys.exc_info()[0])
                print('Context: ', e.__context__)
                print('Value" ', sys.exc_info()[1])
                print('Trace" ', sys.exc_info()[2])

    with open(Const.CG_CONTRACTPATH, 'w') as f:
        json.dump(tokenBook, f, ensure_ascii=False, indent=4)
    cg.session.close()


getCoinGeckoHistory()
# getMarketHistory(coingeckoCoins)
# sortMarketHistory(coingeckoCoins)
# getCourseMarketHistory(coingeckoCoins)


TransactionOrganiser = MainWindow()
TransactionOrganiser.mainloop()
