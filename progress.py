import asyncio
from interactions import CommandContext, Message

import requests

import pandas as pd

class progressBar:
    """
    A progress bar functionality that can display progress on a running process to the discord chat.
    """
    def __init__(
            self, 
            ctx:CommandContext, 
            maxCount:int, 
            autoUpdate:bool = True,
            lit:str = ':blue_square:',
            unlit:str = ':white_large_square:'
    ):
        super().__init__()
        self.context = ctx
        self.maxCount = maxCount
        self.autoUpdate = autoUpdate
        self.currentCount = 0
        self.updateRate = 2
        self.lit = lit
        self.unlit = unlit
    
    async def setupProgressBar(self):
        l = 30
        msg:Message = await self.context.send(f"__{self.unlit*l}__")
        prevP = 0
        while self.currentCount < self.maxCount :
            await asyncio.sleep(self.updateRate)
            p = int(l * (self.currentCount / self.maxCount))
            if prevP == p:
                continue
            prevP = p
            pstr = self.lit*p
            vstr = self.unlit*(l-p)
            await msg.edit(content=f"__{pstr + vstr}__")
        