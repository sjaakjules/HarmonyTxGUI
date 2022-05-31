import json
import os
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import *
from tkinter import filedialog, simpledialog, ttk
from tkinter.messagebox import showinfo

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


class MainWindow(tk.Tk):

    filetypes = (
        ('json files', '*.json'),
        ('All files', '*.*'))

    textMessage = ''
    isLoading = False

    def __init__(self):
        #self.master = master
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
            self.frame, textvariable=self.oneAddress, width=75)
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
            column=0, row=4, columnspan=4, ipadx=10, ipady=10)
        self.ProcessButton.grid_forget()

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

        self.addToText('All done! check CSVs')


class FunctionSelector(tk.Toplevel):

    fnList = {}
    fnCode = ''
    fnTxs = {}
    oneAddress = ''
    allTransactions = {}
    addrGroupedTransactions = {}

    # The lists for combo boxes
    txFnList = []
    uniqueAddr = []
    txList = []

    def __init__(self, TransactionList, oneAddress):
        super().__init__()

        if os.path.exists(Const.FUNCTIONLISTPATH):
            with open(Const.FUNCTIONLISTPATH, 'r') as f:
                self.fnList = json.loads(f.read())
        else:
            print(
                f'Error finding function list. add to "{Const.FUNCTIONLISTPATH}"')

        self.allTransactions = TransactionList
        self.oneAddress = oneAddress

        self.txFnList = []
        for code in TransactionList:
            if code in self.fnList:
                self.txFnList.append(f"{self.fnList[code]['name']} | {code}")
            else:
                self.txFnList.append(f'Unknown | {code}')
        #self.txFnList = list(TransactionList.keys())

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
        self.showOnlyNoLabels = ttk.Button(self.frame,
                                           text='Show Unlabeled Only',
                                           command=self.ShowUnlabeled)
        self.showOnlyNoLabels.grid(
            column=1, row=4, columnspan=1, padx=5, pady=5)
        self.showAll = ttk.Button(self.frame,
                                  text='Show All',
                                  command=self.ShowAll)
        self.showAll.grid(column=1, row=4, columnspan=1, padx=5, pady=5)
        self.showAll.grid_forget()
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

        self.updateAddr(None)

    def LabelFromDefault(self):
        ''

    def ShowUnlabeled(self):
        ''
        self.showOnlyNoLabels.grid_forget()
        self.showAll.grid(column=1, row=4, columnspan=1, padx=5, pady=5)

    def ShowAll(self):
        ''
        self.showAll.grid_forget()
        self.showOnlyNoLabels.grid(
            column=1, row=4, columnspan=1, padx=5, pady=5)

    def digestTxs(self, Transactions, oneAddress):
        self.addrGroupedTransactions = {}
        for i, hash in enumerate(Transactions):
            if Transactions[hash][Const.RECEIPT_KEY]['status'] != 0:
                try:
                    fromAddr = Transactions[hash][Const.TX_KEY]['from']
                    toAddr = Transactions[hash][Const.TX_KEY]['to']
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
                        print('Error, oneAddress not found to or from.')
                except:
                    print(Transactions[hash])
                    break
            else:
                'Transaction did not function.'
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
        print(self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]])
        # with open(Const.FUNCTIONLISTPATH, 'w', encoding='utf-8') as f:
        #    json.dump(self.fnList, f, ensure_ascii=False, indent=4)

    def removeLabeled(self):
        for func in self.FunctionSelector['values']:
            if func.split(' | ', 1)[1] in self.fnList and self.oneAddress in self.fnList[func.split(' | ', 1)[1]]:
                if self.fnList[func.split(' | ', 1)[1]][self.oneAddress]['functionLabel'] != None:
                    self.FunctionSelector['values'].remove(func)

        if self.FunctionSelector.get() not in self.FunctionSelector['values']:
            self.FunctionSelector.set(self.FunctionSelector['values'][0])

        self.updateFunction(None)
        funcCode = self.FunctionSelector.get().split(' | ', 1)[1]
        for Addr in self.AddrSelector['values']:
            if funcCode in self.fnList and self.oneAddress in self.fnList[funcCode]:
                if self.AddrSelector.get() in self.fnList[funcCode][self.oneAddress]['addressLabels']:
                    self.FunctionSelector['values'].remove(func)

        self.AddrSelector['values'] = self.uniqueAddr
        self.AddrSelector.set(self.AddrSelector['values'][0])

        self.TxSelector['values'] = self.addrGroupedTransactions[self.AddrSelector.get()]
        self.TxSelector.set(self.TxSelector['values'][0])

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
        ''
        selectedTx = self.fnTxs[transactionHash]
        displayText = f'Function: {self.fnList[self.fnCode]["name"]} | {self.fnCode}\n'
        '''
        Date:   24-04-14 02:04:14
        from:   one1sdff (me)
        to:     one1asgr (them)
                from (me  -1jd3) to (1sG3-19k4) - 204.214 ONE 
                from (them-1jd3) to (1sG3-19k4) - 204.214 ONE 
        '''
        baseInfo = HmyUtil.getBaseInfo(selectedTx, self.oneAddress)
        displayText += f'\nDate:\t{baseInfo["time"]}'
        displayText += f'\nfrom:\t{baseInfo["from"]}'
        displayText += f'\nto:\t{baseInfo["to"]}'
        for txInfo in HmyUtil.getTransferInfo(selectedTx, self.oneAddress):
            displayText += f'\n  {txInfo["topic"]}\tfrom {txInfo["from"]} to {txInfo["to"]} - {txInfo["amount"]} {txInfo["token"]}'

        self.text.delete('1.0', 'end')
        self.text.insert('1.0', displayText)
        self.updateFunctionLabelDisplays()

    def updateFunctionLabelDisplays(self):
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
                'name': Const.UNKNOWNFUNCTION}

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
        self.updateFunctionLabelDisplays()

    def setAddressLabel(self):
        if self.FunctionSelector.get().split(' | ', 1)[1] not in self.fnList:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]] = {
                'name': Const.UNKNOWNFUNCTION}

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
        self.updateFunctionLabelDisplays()

    def setTransactionLabel(self):
        if self.FunctionSelector.get().split(' | ', 1)[1] not in self.fnList:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]] = {
                'name': Const.UNKNOWNFUNCTION}

        if 'default' not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]['default'] = {
                'functionLabel': '', 'addressLabels': {}, 'transactionLabels': {self.TxSelector.get(): self.labelSelector.get()}}
        else:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                1]]['default']['transactionLabels'][self.TxSelector.get()] = self.labelSelector.get()

        if self.oneAddress not in self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]]:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[1]][self.oneAddress] = {
                'functionLabel': '', 'addressLabels': {}, 'transactionLabels': {self.TxSelector.get(): self.labelSelector.get()}}
        else:
            self.fnList[self.FunctionSelector.get().split(' | ', 1)[
                1]][self.oneAddress]['transactionLabels'][self.TxSelector.get()] = self.labelSelector.get()
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
        if os.path.exists(Const.FUNCTIONLISTPATH):
            with open(Const.FUNCTIONLISTPATH, 'r') as f:
                self.functionList = json.loads(f.read())

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
            column=0, row=4, columnspan=4, ipadx=10, ipady=10)

    def OrganiseTransactions(self):
        self.GUI.addToText(
            '\n------------------------------------------------\nNow Processing!\n')
        self.ManualFunctionLabeler()

        self.GUI.addToText('All done! check CSVs')

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
        pageSize = 100
        expectedTXs = 1
        expectedHRC20s = 1
        try:
            expectedTXs = (account.get_transactions_count(
                self.oneAddress, tx_type='ALL', endpoint=Const.MAINNET0))
            expectedHRC20s = HmyUtil.getHRC20Count(self.oneAddress)
        except BaseException as err:
            self.GUI.addToText(
                f"Writing Log Unexpected {err=}, {type(err)=}\n\t{err.with_traceback}")

        onfileTXCount = 0
        onfileHRC20Count = 0
        fileTxs = {}
        if Const.COUNTSKEY in accountInfoOut:
            onfileTXCount = accountInfoOut[Const.COUNTSKEY][Const.TX_KEY]
            onfileHRC20Count = accountInfoOut[Const.COUNTSKEY][Const.HRC20_KEY]
            fileTxs = accountInfoOut[Const.TRANSACTIONSKEY]
        else:
            accountInfoOut = {Const.COUNTSKEY: {
                Const.TX_KEY: 0, Const.HRC20_KEY: 0, Const.FUNCTION_KEY: [0, 0, 0], Const.RECEIPT_KEY: [0, 0, 0], Const.DECODED_KEY: [0, 0, 0], Const.WEB_KEY: [0, 0, 0]}}

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

        if remainingTxCount == 0:
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
                                fileTxs[tx['ethHash']] = {Const.TX_KEY: tx}
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
                                        ][Const.TX_KEY] = tempTX
                                fileTxs[hrc20['transactionHash']
                                        ][Const.HRC20_KEY] = hrc20
                                newHRC20Count += 1
                            elif Const.HRC20_KEY not in fileTxs[hrc20['transactionHash']]:
                                fileTxs[hrc20['transactionHash']
                                        ][Const.HRC20_KEY] = hrc20
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

        accountInfoOut[Const.COUNTSKEY][Const.TX_KEY] = (
            len(onFileHash) + skippedTxCount+newTxCount)
        accountInfoOut[Const.COUNTSKEY][Const.HRC20_KEY] = (
            skipptedHRC20Count+newHRC20Count)
        accountInfoOut[Const.TRANSACTIONSKEY] = fileTxs

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

        functionCodes = list(orderedFunctions.keys())
        func = FunctionSelector(orderedFunctions, self.oneAddress)
        # func.grab_set()
        print('DONE!!!')

    def PrintTransfersToCSV(self):
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

        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONSKEY]):
            tx = allTransactions[Const.TRANSACTIONSKEY][txHash]
            timestamp = datetime.fromtimestamp(tx[Const.TX_KEY]['timestamp'])
            timestr = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            typeName = tx[Const.FUNCTION_KEY]['function']
            typeCode = tx[Const.FUNCTION_KEY]['code']
            gasFee = tx[Const.TX_KEY]['gasPrice'] * \
                tx[Const.RECEIPT_KEY]['gasUsed'] / (10 ** 18)

            value = tx[Const.TX_KEY]['value'] / (10 ** 18)
            fromInfo = []
            toInfo = []
            unknownInfo = []
            if value != 0:
                if tx[Const.TX_KEY]['from'] == self.oneAddress:
                    fromInfo.append({'amount': value,
                                     'token': 'ONE', 'topic': 'baseTX'})
                elif tx[Const.TX_KEY]['to'] == self.oneAddress:
                    toInfo.append({'amount': value,
                                   'token': 'ONE', 'topic': 'baseTX'})

            if len(tx[Const.RECEIPT_KEY]['logs']) > 0:
                for log in tx[Const.RECEIPT_KEY]['logs']:
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
                csvOut += f'\n{timestr},{typeName},{typeCode},{t["topic"]},{t["token"]},{t["amount"]},from,{gasFee},{tx[Const.TX_KEY]["ethHash"]}'
            for t in toInfo:
                csvOut += f'\n{timestr},{typeName},{typeCode},{t["topic"]},{t["token"]},{t["amount"]},to,{gasFee},{tx[Const.TX_KEY]["ethHash"]}'
            for t in unknownInfo:
                unknownCsvOut += f'\n{timestr},{typeName},{typeCode},{t["topic"]},{t["token"]},{t["amount"]},unknown,{gasFee},{tx[Const.TX_KEY]["ethHash"]}'

        with open(f'./CSV Outputs/test_{self.oneAddress}.csv', 'w') as f:
            f.write(csvOut)
        with open(f'./CSV Outputs/test_{self.oneAddress}_unkown.csv', 'w') as f:
            f.write(unknownCsvOut)

    def getfunctionSorted(self, allTransactions) -> dict:
        transactionsOut = {}
        for i, txHash in enumerate(allTransactions[Const.TRANSACTIONSKEY]):
            tx = allTransactions[Const.TRANSACTIONSKEY][txHash]
            typeCode = tx[Const.FUNCTION_KEY]['code']
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
        maxAttempts = 5

        timeLast = time.perf_counter()
        lastAmount = 0
        '''[New,Skipped,Unknown]'''
        counters = {Const.RECEIPT_KEY: [0, 0, 0],
                    Const.DECODED_KEY: [0, 0, 0],
                    Const.FUNCTION_KEY: [0, 0, 0],
                    Const.WEB_KEY: [0, 0, 0]}
        hasNew = False
        for i, (hash) in enumerate(accountDetails[Const.TRANSACTIONSKEY]):
            txInfo = accountDetails[Const.TRANSACTIONSKEY][hash]
            # Per transaction
            willUpdateTx = {}
            if Const.TRANSACTIONSKEY in accountOut and hash in accountOut[Const.TRANSACTIONSKEY]:
                'The item is in TxOut'
                if Const.COUNTSKEY not in accountOut[Const.TRANSACTIONSKEY][hash]:
                    accountOut[Const.TRANSACTIONSKEY][hash][Const.COUNTSKEY] = {
                        Const.RECEIPT_KEY: 0, Const.DECODED_KEY: 0, Const.FUNCTION_KEY: 0, Const.WEB_KEY: 0}
            # if the ethHash is not in 'TxOut' (previousely compleated) then add web info
                for (decodeKey) in counters:
                    countValues = counters[decodeKey]
                    willUpdateTx[decodeKey] = False
                    if decodeKey in accountOut[Const.TRANSACTIONSKEY][hash]:
                        'has decoded info'
                        if Const.NOVALUE in accountOut[Const.TRANSACTIONSKEY][hash][decodeKey]:
                            'There is no value'
                            accountOut[Const.TRANSACTIONSKEY][hash][decodeKey][Const.NOVALUE] += 1
                            if accountOut[Const.TRANSACTIONSKEY][hash][decodeKey][Const.NOVALUE] < maxAttempts:
                                willUpdateTx[decodeKey] = True
                            else:
                                countValues[2] += 1
                        elif Const.UNKNOWNFUNCTION in accountOut[Const.TRANSACTIONSKEY][hash][decodeKey]:
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
                    Const.RECEIPT_KEY: True, Const.DECODED_KEY: True, Const.FUNCTION_KEY: True, Const.WEB_KEY: True}
                accountOut[Const.TRANSACTIONSKEY][hash] = txInfo

            for (deKey) in willUpdateTx:
                willUpdate = willUpdateTx[deKey]
                if willUpdate:
                    hasNew = True
                    if len(accountOut[Const.TRANSACTIONSKEY][hash][Const.TX_KEY]['input']) >= 10:
                        functionCode = accountOut[Const.TRANSACTIONSKEY][hash][Const.TX_KEY]['input'][0:10]
                    else:
                        functionCode = accountOut[Const.TRANSACTIONSKEY][hash][Const.TX_KEY]['input']
                    match deKey:
                        case Const.RECEIPT_KEY:
                            'will update receipt'
                            try:
                                recpt = transaction.get_transaction_receipt(
                                    txInfo[Const.TX_KEY]['ethHash'].lower(), Const.MAINNET0)
                                counters[deKey][0] += 1
                            except BaseException as err:
                                recpt = {
                                    Const.NOVALUE: maxAttempts, 'function': Const.ERRORFUNCTION, 'data': f'Unexpected {err=}, {type(err)=}'}
                                counters[deKey][2] += 1

                            accountOut[Const.TRANSACTIONSKEY][hash][deKey] = recpt
                        case Const.DECODED_KEY:
                            'decode vairable'
                            if ABIs == None:
                                accountOut[Const.TRANSACTIONSKEY][hash][deKey] = {
                                    Const.UNKNOWNFUNCTION: maxAttempts, "function": Const.UNKNOWNFUNCTION, 'code': functionCode}
                                counters[deKey][2] += 1
                            else:
                                try:
                                    for tempABI in ABIs:
                                        decoded = HmyUtil.decode_tx(
                                            HmyUtil.convert_one_to_hex(txInfo[Const.TX_KEY]['to']), txInfo[Const.TX_KEY]['input'], tempABI)

                                        if decoded[2] is not None:
                                            accountOut[Const.TRANSACTIONSKEY][hash][deKey] = {
                                                "function": decoded[0], "data": json.loads(decoded[1])}
                                            counters[deKey][0] += 1
                                            break
                                    if decoded[2] is None:
                                        accountOut[Const.TRANSACTIONSKEY][hash][deKey] = {
                                            Const.NOVALUE: maxAttempts, 'function': Const.NOVALUE}
                                        counters[deKey][2] += 1

                                except BaseException as err:
                                    accountOut[Const.TRANSACTIONSKEY][hash][deKey] = {
                                        Const.NOVALUE: maxAttempts, 'function': Const.ERRORFUNCTION, 'data': f'Unexpected {err=}, {type(err)=}'}
                                    counters[deKey][2] += 1
                        case Const.FUNCTION_KEY:
                            'add function'
                            functionName = HmyUtil.getFunctionName(
                                functionList, accountOut[Const.TRANSACTIONSKEY][hash][Const.TX_KEY])
                            if(functionName != Const.UNKNOWNFUNCTION):
                                "Decoded function"
                                counters[deKey][0] += 1
                            else:
                                "Unknown function"
                                counters[deKey][2] += 1
                            accountOut[Const.TRANSACTIONSKEY][hash][deKey] = {
                                "function": functionName, 'code': functionCode}
                        case Const.WEB_KEY:
                            'add web'
                            accountOut[Const.TRANSACTIONSKEY][hash][deKey] = {
                                Const.UNKNOWNFUNCTION: maxAttempts, "function": Const.UNKNOWNFUNCTION, 'code': functionCode}
                            counters[deKey][2] += 1
                        case _:
                            print(f'Error, No catch for key {deKey}')
            'Updated all '

            '''timerlast = HmyUtil.printUpdate(timerstart, timerlast, 3, 100*i/len(accountDetails[oneAddy][Const.TRANSACTIONSKEY]),
                                            f"Tx {i}/{len(accountDetails[oneAddy][Const.TRANSACTIONSKEY])}: {counters}")'''
            counterDisplay = []
            for key in counters:
                accountOut[Const.COUNTSKEY][key] = counters[key]
                counterDisplay.append(
                    [key, *counters[key], sum(counters[key])])
            if hasNew and i % 250 == 0:
                hasNew = False
                with open(self.outputJSONFile, 'w', encoding='utf-8') as f:
                    json.dump(accountOut, f, ensure_ascii=False, indent=4)

            (timeLast, lastAmount) = self.simpleLoadingUpdate(timeLast, lastAmount, len(accountDetails[Const.TRANSACTIONSKEY]), i,
                                                              f"Tx {i}/{len(accountDetails[Const.TRANSACTIONSKEY])}")
        counterDisplay = []
        for key in counters:
            accountOut[Const.COUNTSKEY][key] = counters[key]
            counterDisplay.append([key, *counters[key], sum(counters[key])])

        self.GUI.addToText(
            '\n'+tabulate(counterDisplay, headers=['', 'New', 'Skipped', 'Unknown', 'Total'])+'\n')

        with open(self.outputJSONFile, 'w', encoding='utf-8') as f:
            json.dump(accountOut, f, ensure_ascii=False, indent=4)
            self.GUI.addToText(
                f"\n\nSaved {len(accountOut[Const.TRANSACTIONSKEY])} transactions to {self.outputJSONFile}\n")

        return accountOut


TransactionOrganiser = MainWindow()
TransactionOrganiser.mainloop()
