
LOGPATH = 'log.txt'
FUNCTIONLISTPATH = './TokenInfo/FunctionList.json'
HRC20LISTPATH = './TokenInfo/HRC20Tokens.json'
TXOUTPATH = './TransactionHistory/'

TRANSACTIONS_KEY = 'transactions'
COUNTS_KEY = 'counts'
TXLIST = 'txList'

ADDRESSBOOKPATH = './TransactionHistory/AddressBook.json'
AB_ONE = 'one'
AB_HEX = 'hex'
AB_NAME = 'name'
AB_LABEL = 'labels'
AB_UNKNOWN = 'Unknown'

MM_HARMONYCHAIN = '0x63564c40'
MM_DFKCHAIN = '0xd2af'
MM_BASE = 'metamask'
MM_ADDR = 'addressBook'
MMA_ADDR = 'address'
MMA_NAME = 'name'

CG_CONTRACTPATH = './TokenInfo/CoinGeckoContracts.json'
CG_ID = "geckoID"
CG_CHAINID = "chainID"
CG_CONTRACT = "contract"
CG_NAME = "name"
CG_ISONLINE = "inCoinGecko"

C_INFO = "CoinInfo"
C_COARSE_USD = "CoarseUSD"
C_COARSE_AUD = "CoarseAUD"
C_FINE_USD = "FineUSD"
C_FINE_AUD = "FineAUD"
C_SFINE_USD = "SuperFineUSD"
C_SFINE_AUD = "SuperFineAUD"
C_OLDTIME = "oldest"
C_NEWTIME = "newest"

K_TIME = 'time'
K_SENT = 'sent'
K_SCOIN = 'sentCoin'
K_REC = 'received'
K_RCOIN = 'receivedCoin'
K_FEE = 'fee'
K_FCOIN = 'feeCoin'
K_VALUE = 'value'
K_VCOIN = 'fiat'
K_LABEL = 'label'
K_NOTES = 'notes'
K_HASH = 'hash'

T_TX_KEY = 'Txs'
T_HRC20_KEY = 'HRC20'
T_FUNCTION_KEY = 'Function'
T_RECEIPT_KEY = 'Receipt'
T_DECODED_KEY = 'Decoded'
T_WEB_KEY = 'Web'

F_DEFAULT_KEY = 'default'
F_CODE_KEY = 'code'
F_NAME_KEY = 'name'

#'''Used for each transaction within Tx[TRANSACTIONS_KEY][T_FUNCTION_KEY]'''
TF_FROM = 'from'
TF_TO = 'to'
TF_THEIR = 'their'
TF_TIME = 'time'
TF_FUNCNAME = 'name'
TF_FUNCCODE = 'code'
TF_GAS = 'gas'
TF_TRADES = 'trades'
TF_SORTTRADES = 'trades'
TF_UKTRADES = 'unknownTrades'
TF_FUNCLABEL = 'label'

#'''Used for each trade within Tx[TRANSACTIONS_KEY][T_FUNCTION_KEY][TF_TRADES]'''
TFT_FROM = 'from'
TFT_TO = 'to'
TFT_THEIR = 'their'
TFT_SENTAMOOUNT = 'sentAmount'
TFT_SENTTOKEN = 'sentToken'
TFT_RECAMOUNT = 'receivedAmount'
TFT_RECTOKEN = 'receivedToken'
TFT_TOPIC = 'topic'
TFT_CSVLABEL = 'label'
TFT_NOTES = 'notes'
TFT_TCONT = 'TokenContract'
TFT_TAMOUNT = 'TotalAmount'
TFT_TNAME = 'TokenName'

FUNC_NOVALUE = 'NoValue'        # There is no function name or value.
# There is a function name or value but was not able to resolve entry.
FUNC_UNKNOWN = 'Unknown'
FUNC_UNDEFINED = 'Undefined'    # There might or might not be a name or value.
FUNC_ERROR = 'ErrorOut'         # There was an error resolving name or value.


BSC_ID = '0x38'
HARMONY_ID = '0x63564c40'
DFK_ID = '0xd2af'

TESTNET0 = 'https://api.s0.b.hmny.io'				# this is shard 0
TESTNET1 = 'https://api.s1.b.hmny.io'
TESTADDRESS = 'one18t4yj4fuutj83uwqckkvxp9gfa0568uc48ggj7'

MAINNET0 = 'https://rpc.s0.t.hmny.io'
MAINNET0B = 'https://a.api.s0.t.hmny.io'#'https://rpc.s0.t.hmny.io'
MAINNET1 = 'https://rpc.s1.t.hmny.io'
MAINNET2 = 'https://a.api.s0.t.hmny.io'
ENDPOINT = 'https://explorer-v2-api.hmny.io/v0/'

ONE = '0xcf664087a5bb0237a0bad6742852ec6c8d69a27a'


LOGTOPICS = {
    '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef': 'Transfer',
    '0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925': 'Approval',
    '0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f': 'Mint',
    '0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04': 'AccruInterest',
    '0x71bab65ced2e5750775a0613be067df48ef06cf92a496ebf7663ae0660924954': 'Harvest',
    '0x8b3e96f2b889fa771c53c981b40daf005f63f637f1869f707052d15a3dd97140': 'Token Exchange',
    '0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1': 'Repay Borrow',
    '0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80': 'Borrow',
    '0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c': 'Deposit',
    '0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929': 'Redeem',
    '0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496': 'Burn',
    '0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1': 'Sync',
    '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822': 'Swap',
    '0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65': 'Withdrawal'
}

KNOWNADDRESS = [
    # 0xaa9a289ce0565e4d6548e63a441e7c084e6b52f6
    {'one142dz388q2e0y6e2gucayg8nupp8xk5hk62auhh': 'DKF Quest'},
    {'0x9014B937069918bd319f80e8B3BB4A2cf6FAA5F7': 'DFK UniswapV2Factory'},
    {'0x24ad62502d1C652Cc7684081169D04896aC20f30': 'DFK UniswapV2Router02'},
    {'0x72Cb10C6bfA5624dD07Ef608027E366bd690048F': 'DFK JewelToken'},
    {'0xA9cE83507D872C5e1273E745aBcfDa849DAA654F': 'DFK xJEWEL'},
    {'0x3685Ec75Ea531424Bbe67dB11e07013ABeB95f1e': 'DFK Banker'},
    {'0xDB30643c71aC9e2122cA0341ED77d09D5f99F924': 'DFK MasterGardener'},
    {'0xa678d193fEcC677e137a00FEFb43a9ccffA53210': 'DFK Airdrop'},
    {'0x6391F796D56201D279a42fD3141aDa7e26A3B4A5': 'DFK Profiles'},
    {'0x5F753dcDf9b1AD9AabC1346614D1f4746fd6Ce5C': 'DFK Hero'},
    {'0x24eA0D436d3c2602fbfEfBe6a16bBc304C963D04': "DFK Gaia's Tears"},
    {'0x3a4edcf3312f44ef027acfd8c21382a5259936e7': 'DFK Gold'},
    {'0xe4154B6E5D240507F9699C730a496790A722DF19': 'DFK Gardening Quest'},
    {'0x9CC714059943D5A726fAD11087Bb6d9Ab811A2E3': 'DFK Graveyard Contract'}
]
