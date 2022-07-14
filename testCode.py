import json
from typing import Dict, List

import requests

import src.HmyTx_Constants as C
import src.HmyTx_Utils as util


def getHRC20Count(oneAddy) -> int:
    HRC20Counter = []
    attempts = 10
    count = 0
    limit = 2500
    offset = 0
    while count < attempts:
        try:
            i = 0
            while True:
                i +=1
                print(f'\nAttempt {i}:')
                url = f'{C.ENDPOINT}shard/0/address/{util.convert_one_to_hex(oneAddy).lower()}/transactions/type/erc20?offset={offset}&limit={limit}'
                response = requests.get(url)
                jsonResponse = []
                if response.status_code == 200:
                    jsonResponse = json.loads(response.text)
                    HRC20Counter.extend(jsonResponse)
                    offset += limit
                else:
                    print(f'Error. Status code: {response.status_code}')
                    break

                if len(jsonResponse) != limit:
                    count = attempts
                    break

        except BaseException as err:
            print(f'Error getting count. Status code: {response.status_code}')
            print(f"{count}: Writing Log Unexpected {err=}, {type(err)=}\n\t{err.with_traceback}")
        count += 1

    print(f'Expecting {len(HRC20Counter)} HRC20 transactions.')
    return len(HRC20Counter)


"""
# Online Python compiler (interpreter) to run Python online.
# Write Python 3 code in this online editor and run it.
class agent:
    age = 0

    def __init__(self):
        age = 2

    def blowjob(self, sally: int) -> int:
        age = 3
        return age


#agentDic = {'hello': []}

agentList: List[agent] = []
agentDic: Dict[str:List[agent]] = {}
var = agentDic['hello'][0]

z: agent
for z in agentDic['hello']:
    ''


for i in range(10):
    agentList.append(agent())
print('done')
"""
