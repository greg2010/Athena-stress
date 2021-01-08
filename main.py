import requests
import aiohttp
import asyncio
import time
import numpy as np
import os

def getRiotSumNames(regions):
    key = os.getenv('RIOT_API_KEY')
    names = []
    for region in regions:
        endpoint = "https://{}.api.riotgames.com/lol/spectator/v4/featured-games".format(region)
        headers = {'X-Riot-Token': key}
        r = requests.get(endpoint, headers=headers).json()
        names.extend(list(map(lambda x: (region, x['participants'][0]['summonerName']), r['gameList'])))

    return names

def getMobaSumName():
    url = "https://app.mobalytics.gg/api/lol/graphql/v1/query"
    headers = {'Content-type': 'application/json'}
    postData = """
    {
    "operationName": "LiveGamesQuery",
    "variables": {
        "top": 72,
        "skip": 0,
        "tier": null,
        "region": null,
        "champion": null
    },
    "query": "query LiveGamesQuery($region: Region, $champion: ID, $tier: SummonerTier, $skip: Int!, $top: Int!) {  lol {    liveGames(top: $top, skip: $skip, region: $region, champion: $champion, tier: $tier) {      games {        ...LiveGameFragment        __typename      }      total      __typename    }    __typename  }}fragment LiveGameFragment on LiveGame {  participants {     summoner {      name region }  }}"
}
    """
    r = requests.post(url, postData, headers=headers).json()
    names = map(lambda x: (x['participants'][0]['summoner']['region'] + '1', x['participants'][0]['summoner']['name']), r['data']['lol']['liveGames']['games'])
    return list(names)


async def sendRequestFor(session, region, name):
    endpoint = "{}/current/by-summoner-name/{}/{}/groups".format(os.getenv('ATHENA_BASE_URL'), region, name)
    start = time.monotonic()
    async with session.get(endpoint) as r:
        delta = time.monotonic() - start
        print("Got response for region={} name={} code={} completed_in={}s".format(region, name, r.status, delta))
        return (r, delta)


async def runMain():
    # Regions to test
    regions = ['NA1', 'EUW1', 'BR1', 'EUN1', 'JP1', 'KR', 'LA1', 'LA2', 'OC1', 'TR1']
    # Fetch riot featured games
    riotSumNames = getRiotSumNames(regions)
    # Fetch Mobalytics featured games
    mobaSumNames = getMobaSumName()
    # Hardcode some NA pro accounts
    naProNames = ['Qwacker', 'FTWWW', 'Matty', 'CE Fed', 'Hakuho', 'Blitz', 'TF Blade', 'ShorterACE', 'Command Attack', 'Red Robin']
    naQNames = list(map(lambda x: ('NA1', x), naProNames))
    names = riotSumNames + mobaSumNames + naQNames
    names = names + names + names

    print("Got summoner names {}".format(names))
    print("Sending {} requests".format(len(names)))

    startTotal = time.monotonic()
    tasks = []
    async with aiohttp.ClientSession() as session:
        for n in names:
            task = asyncio.ensure_future(sendRequestFor(session, n[0], n[1]))
            tasks.append(task)
        responses = asyncio.gather(*tasks)
        rr = await responses
        avg = np.array(list(map(lambda x: x[1], rr))).mean()
        print("Response time mean: {}s".format(avg))


    endTotal = time.monotonic()
    print("Total time: {}s".format(endTotal - startTotal))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runMain())


