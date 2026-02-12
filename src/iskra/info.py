"""
iskra info - repo stats at a glance.

Like onefetch but cooler. Shows languages, contributors, commit count,
lines of code, license, all that good stuff. With ASCII art from onefetch!
"""

import os
import subprocess
import re
from collections import Counter
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich import box


console = Console()


# ASCII art for languages (from onefetch - https://github.com/o2sh/onefetch)
LANG_ASCII = {
    "C": [
        "[cyan]                 ++++++[/]",
        "[cyan]              ++++++++++++[/]",
        "[cyan]          ++++++++++++++++++++[/]",
        "[cyan]       ++++++++++++++++++++++++++[/]",
        "[cyan]    ++++++++++++++++++++++++++++++++[/]",
        "[cyan] +++++++++++++[/][white]************[/][cyan]+++++++++++++[/]",
        "[cyan]+++++++++++[/][white]******************[/][cyan]++++++++[/][blue];;;[/]",
        "[cyan]+++++++++[/][white]**********************[/][cyan]++[/][blue];;;;;;;[/]",
        "[cyan]++++++++[/][white]*********[/][cyan]++++++[/][white]******[/][blue];;;;;;;;;;;[/]",
        "[cyan]+++++++[/][white]********[/][cyan]++++++++++[/][white]**[/][blue];;;;;;;;;;;;;[/]",
        "[cyan]+++++++[/][white]*******[/][cyan]+++++++++[/][blue];;;;;;;;;;;;;;;;;[/]",
        "[cyan]+++++++[/][white]******[/][cyan]+++++++[/][blue];;;;;;;;;;;;;;;;;;;;[/]",
        "[cyan]+++++++[/][white]*******[/][cyan]+++[/][blue]:::::[/][blue];;;;;;;;;;;;;;;;;;[/]",
        "[cyan]+++++++[/][white]********[/][blue]::::::::::[/][white]**[/][blue];;;;;;;;;;;;;[/]",
        "[cyan]++++++++[/][white]*********[/][blue]::::::[/][white]******[/][blue];;;;;;;;;;;[/]",
        "[cyan]++++++[/][blue]:::[/][white]**********************[/][blue]::[/][blue];;;;;;;[/]",
        "[cyan]+++[/][blue]::::::::[/][white]******************[/][blue]::::::::[/][blue];;;[/]",
        "[blue] :::::::::::::[/][white]************[/][blue]:::::::::::::[/]",
        "[blue]    ::::::::::::::::::::::::::::::::[/]",
        "[blue]       ::::::::::::::::::::::::::[/]",
        "[blue]          ::::::::::::::::::::[/]",
        "[blue]              ::::::::::::[/]",
        "[blue]                 ::::::[/]",
    ],
    "C++": [
        "[cyan]                 ++++++[/]",
        "[cyan]              ++++++++++++[/]",
        "[cyan]          ++++++++++++++++++++[/]",
        "[cyan]       ++++++++++++++++++++++++++[/]",
        "[cyan]    ++++++++++++++++++++++++++++++++[/]",
        "[cyan] +++++++++++++[/][white]************[/][cyan]+++++++++++++[/]",
        "[cyan]+++++++++++[/][white]******************[/][cyan]++++++++[/][blue];;;[/]",
        "[cyan]+++++++++[/][white]**********************[/][cyan]++[/][blue];;;;;;;[/]",
        "[cyan]++++++++[/][white]*********[/][cyan]++++++[/][white]******[/][blue];;;;;;;;;;;[/]",
        "[cyan]+++++++[/][white]********[/][cyan]++++++++++[/][white]**[/][blue];;;;;;;;;;;;;[/]",
        "[cyan]+++++++[/][white]*******[/][cyan]+++++++++[/][blue];;;;;;[/][white]**[/][blue];;;;[/][white]**[/][blue];;;[/]",
        "[cyan]+++++++[/][white]******[/][cyan]+++++++[/][blue];;;;;;;;[/][white]****[/][blue];;[/][white]****[/][blue];;[/]",
        "[cyan]+++++++[/][white]*******[/][cyan]+++[/][blue]:::::[/][blue];;;;;;;[/][white]**[/][blue];;;;[/][white]**[/][blue];;;[/]",
        "[cyan]+++++++[/][white]********[/][blue]::::::::::[/][white]**[/][blue];;;;;;;;;;;;;[/]",
        "[cyan]++++++++[/][white]*********[/][blue]::::::[/][white]******[/][blue];;;;;;;;;;;[/]",
        "[cyan]++++++[/][blue]:::[/][white]**********************[/][blue]::[/][blue];;;;;;;[/]",
        "[cyan]+++[/][blue]::::::::[/][white]******************[/][blue]::::::::[/][blue];;;[/]",
        "[blue] :::::::::::::[/][white]************[/][blue]:::::::::::::[/]",
        "[blue]    ::::::::::::::::::::::::::::::::[/]",
        "[blue]       ::::::::::::::::::::::::::[/]",
        "[blue]          ::::::::::::::::::::[/]",
        "[blue]              ::::::::::::[/]",
        "[blue]                 ::::::[/]",
    ],
    "Clojure": [
        "[cyan]                 ,,,,,[/]",
        "[cyan]           .-/+ooooooooo+/:-`[/]",
        "[cyan]        ./ooooooooooooooooooo+:.[/]",
        "[cyan]      -+oooooooooooooooooooooooo+-[/]",
        "[cyan]    ,+ooooooooo+/:---::/+ooooooooo+.[/]",
        "[cyan]                        `-/oosoooooo:[/]",
        "[green]   .,,oooo/'      [/][cyan]:\\\\\\\\\\,  `\\oooooooo:[/]",
        "[green]  :,ooooo-  :///:  [/][cyan]:\\\\\\\\\\\\,  -oooooooo-[/]",
        "[green] :oooooo:  ://///:  [/][cyan]:\\\\\\\\\\\\\\,  :oooooo+[/]",
        "[green].ooooooo  :///////:  [/][cyan]:\\\\\\\\\\\\\\,  ooooooo.[/]",
        "[green]:oooooo+  ://////:    [/][cyan]:\\\\\\\\\\\\,  +oooooo:[/]",
        "[green]-ooooooo`  :////:  ::  [/][cyan]:\\\\\\\\\\, 'ooooooo-[/]",
        "[green]`ooooooo:   ://:  ://:  [/][cyan]:\\\\\\,  /oooooo:[/]",
        "[green] -ooooooo:   ::  :////:  [/][cyan]:\\:  :ooooo,:[/]",
        "[green]  :ooooooo+.    ://////:    [/][cyan].+oooo,,.[/]",
        "[green]   :oooooooo+-`[/]",
        "[green]    .+ooooooooo+/::::://oooooooooo+'[/]",
        "[green]      -+oooooooooooooooooooooooo+-[/]",
        "[green]        .:ooooooooooooooooooo+:.[/]",
        "[green]           `-:/ooooooooo+/:.`[/]",
        "[green]                 ``````[/]",
    ],
    "Dart": [
        "[blue]#[/]",
        "[blue] ##[/]",
        "[blue]  ###[/]",
        "[blue]   ######              ###[/]",
        "[blue]    #########        #######[/]",
        "[blue]      ###########  ######[/][blue]O[/][blue]##[/][blue]========-[/]",
        "[blue]       #####################[/]",
        "[blue]         ##################[/]",
        "[blue]      ###############[/][cyan]+++++[/]",
        "[blue]###################[/][cyan]+++++++[/]",
        "[blue]        ##########[/][cyan]+++++++[/]",
        "[blue]               ##[/][cyan]+++++++[/]",
        "[blue]               ###[/][cyan]+++[/]",
        "[blue]               #####[/]",
        "[blue]               #######[/]",
        "[blue]               #########[/]",
        "[blue]                #######[/]",
        "[blue]                 #####[/]",
    ],
    "Elixir": [
        "[magenta]            x[/]",
        "[magenta]           WNX[/]",
        "[magenta]          Odc:x[/]",
        "[magenta]        0ddko,oX[/]",
        "[magenta]       kokNWOllOW[/]",
        "[magenta]     KdoKWMMNKxl0W[/]",
        "[magenta]    0odXMMMMMMNxoON[/]",
        "[magenta]   0lxNMMMMMMMMW0dd0N[/]",
        "[magenta]  0oxNMMMMMMMMMMMNOodKW[/]",
        "[magenta] xodXMMMMMMMMMMMMMMXxokN[/]",
        "[magenta]xol0MMMMMMMMMMMMMMMMW0odX[/]",
        "[magenta]xoxWMMMMMMMMMMMMMMMMMMKodN[/]",
        "[magenta]0lOMMMMMMMMMMMMMMMMMMMWOlO[/]",
        "[magenta]OlOMWKXMMMMMMMMMMMMMMMMKlxW[/]",
        "[magenta]KlxWXodNMMMMMMMMMMMMMMM0lkW[/]",
        "[magenta]xxoKWOlkNMMMMMMMMMMMMMWkl0[/]",
        "[magenta] XooKN0ddkKNWWWMMMMMMWOlkW[/]",
        "[magenta]  XxokXN0kxxkkKMMMMN0doON[/]",
        "[magenta]   WKxdxk0KKKKXK0OxddkXW[/]",
        "[magenta]     WNKOxxxxxxxxkOXW[/]",
        "[magenta]         WWWWWWW[/]",
    ],
    "Erlang": [
        "[red]   EEEEEEEEEEEEE      EEEEEEEEEEEE[/]",
        "[red]  EEEEEEEEEEEE         EEEEEEEEEEEE[/]",
        "[red] EEEEEEEEEEEE           EEEEEEEEEEE[/]",
        "[red] EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE[/]",
        "[red]EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE[/]",
        "[red]EEEEEEEEEEEEE[/]",
        "[red]EEEEEEEEEEEEE[/]",
        "[red]EEEEEEEEEEEEE[/]",
        "[red] EEEEEEEEEEEEE                 E[/]",
        "[red] EEEEEEEEEEEEE                EEEEE[/]",
        "[red]  EEEEEEEEEEEEE             EEEEEEEEE[/]",
        "[red]   EEEEEEEEEEEEEE         EEEEEEEEEE[/]",
    ],
    "Go": [
        "[cyan]           --==============--[/]",
        "[cyan]  .-==-.===oooo=oooooo=ooooo===--===-[/]",
        "[cyan] .==  =o=[/][white]oGGGGGG[/][cyan]o=oo=o[/][white]GGGGGGG[/][cyan]G=o=  oo-[/]",
        "[cyan] -o= oo=[/][white]G .=GGGGG[/][cyan]o=o=[/][white]= .=GGGGG[/][cyan]=ooo o=-[/]",
        "[cyan]  .-=oo=[/][white]o==oGGGGG[/][cyan]=oo=[/][white]oooGGGGGo[/][cyan]=oooo.[/]",
        "[cyan]   -ooooo[/][white]=oooooo[/][cyan]=[/][yellow].   .[/][cyan]=[/][white]=ooo==[/][cyan]oooooo-[/]",
        "[cyan]   -ooooooooooo[/][yellow]====_====[/][cyan]ooooooooooo=[/]",
        "[cyan]   -oooooooooooo[/][yellow]==[/][white]#[/][cyan].[/][white]#[/][yellow]==[/][cyan]ooooooooooooo[/]",
        "[cyan]   -ooooooooooooo=[/][white]#[/][cyan].[/][white]#[/][cyan]=oooooooooooooo[/]",
        "[cyan]   .oooooooooooooooooooooooooooooooo.[/]",
        "[cyan]    oooooooooooooooooooooooooooooooo.[/]",
        "[yellow]  ..[/][cyan]oooooooooooooooooooooooooooooooo[/][yellow]..[/]",
        "[yellow]-=o-[/][cyan]=ooooooooooooooooooooooooooooooo[/][yellow]-oo.[/]",
        "[yellow].=- [/][cyan]oooooooooooooooooooooooooooooooo[/][yellow]-.-[/]",
        "[cyan]   .oooooooooooooooooooooooooooooooo-[/]",
        "[cyan]   -oooooooooooooooooooooooooooooooo-[/]",
        "[cyan]   -oooooooooooooooooooooooooooooooo-[/]",
        "[cyan]   -oooooooooooooooooooooooooooooooo-[/]",
        "[cyan]   .oooooooooooooooooooooooooooooooo[/]",
        "[cyan]    =oooooooooooooooooooooooooooooo-[/]",
        "[cyan]    .=oooooooooooooooooooooooooooo-[/]",
        "[cyan]      -=oooooooooooooooooooooooo=.[/]",
        "[yellow]     =oo[/][cyan]====oooooooooooooooo==-[/][yellow]oo=-[/]",
        "[yellow]    .-==-    [/][cyan].--=======---     [/][yellow].==-[/]",
    ],
    "Haskell": [
        "[cyan]yyyyyy[/][magenta] xxxxxx[/]",
        "[cyan] yyyyyy[/][magenta] xxxxxx[/]",
        "[cyan]  yyyyyy[/][magenta] xxxxxx[/]",
        "[cyan]   yyyyyy[/][magenta] xxxxxx[/]",
        "[cyan]    yyyyyy[/][magenta] xxxxxx[/][blue] yyyyyyyyyy[/]",
        "[cyan]     yyyyyy[/][magenta] xxxxxx[/][blue] yyyyyyyyy[/]",
        "[cyan]      yyyyyy[/][magenta] xxxxxx[/]",
        "[cyan]     yyyyyy[/][magenta] xxxxxxxx[/][blue] yyyyyyy[/]",
        "[cyan]    yyyyyy[/][magenta] xxxxxxxxxx[/][blue] yyyyyy[/]",
        "[cyan]   yyyyyy[/][magenta] xxxxxxxxxxxx[/]",
        "[cyan]  yyyyyy[/][magenta] xxxxxx  xxxxxx[/]",
        "[cyan] yyyyyy[/][magenta] xxxxxx    xxxxxx[/]",
        "[cyan]yyyyyy[/][magenta] xxxxxx      xxxxxx[/]",
    ],
    "Java": [
        "[red]                  |[/]",
        "[red]                 ||[/]",
        "[red]               |||[/]",
        "[red]             ||||    ||[/]",
        "[red]           ||||| ||||[/]",
        "[red]          ||||  |||[/]",
        "[red]         ||||  |||[/]",
        "[red]         |||    |||[/]",
        "[red]          |||    |||[/]",
        "[red]            ||    ||[/]",
        "[red]              |   |[/]",
        "[blue]   ####               #    ##[/]",
        "[blue]    ################       ##[/]",
        "[blue]       #                   ##[/]",
        "[blue]      ################   ###[/]",
        "[blue][/]",
        "[blue]       ##############[/]",
        "[blue]####      #######          #[/]",
        "[blue]#####                   ####[/]",
        "[blue]   #####################      #[/]",
        "[blue]                          ###[/]",
        "[blue]          ###############[/]",
    ],
    "JavaScript": [
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJ    SJSJS      JSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJ    SJS          JSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJ    SJS     JSJSJSJSJ[/]",
        "[yellow]JSJSJSJSJSJSJSJSJ    SJSJ     SJSJSJSJ[/]",
        "[yellow]JSJSJSJSJSJSJSJSJ    SJSJSJ     SJSJSJ[/]",
        "[yellow]JSJSJSJSJSJSJSJSJ    SJSJSJSJ     JSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJ    SJSJSJSJS     JSJ[/]",
        "[yellow]JSJSJSJSJS     JS    JSJS          JSJ[/]",
        "[yellow]JSJSJSJSJSJ          SJSJSJ      SJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
        "[yellow]JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS[/]",
    ],
    "Kotlin": [
        "[blue]KOTLIN[/][magenta]KOTLINKOTLINKO[/][yellow]TLINKOTLINKOTLINKOTL[/]",
        "[blue]KOTLINKO[/][magenta]TLINKOTLIN[/][yellow]KOTLINKOTLINKOTLINKO[/]",
        "[blue]KOTLINKOTL[/][magenta]INKOTL[/][yellow]INKOTLINKOTLINKOTLIN[/]",
        "[blue]KOTLINKOTLIN[/][magenta]KO[/][yellow]TLINKOTLINKOTLINKOTL[/]",
        "[blue]KOTLINKOTLIN[/][yellow]KOTLINKOTLINKOTLINKO[/]",
        "[blue]KOTLINKOTL[/][yellow]INKOTLINKOTLINKOTLIN[/]",
        "[blue]KOTLINKO[/][yellow]TLINKOTLINKOTLINKOTL[/]",
        "[blue]KOTLIN[/][yellow]KOTLINKOTLINKOTLINKO[/]",
        "[blue]KOTL[/][yellow]INKOTLINKOTLINKOTLIN[/]",
        "[blue]KO[/][yellow]TLINKOTLINKOTLINKOTL[/]",
        "[yellow]KOTLINKOTLINKOTLINKO[/][magenta]TL[/]",
        "[magenta]KO[/][yellow]TLINKOTLINKOTLIN[/][magenta]KOTLIN[/]",
        "[magenta]KOTL[/][yellow]INKOTLINKOTL[/][magenta]INKOTLINKO[/]",
        "[magenta]KOTLIN[/][yellow]KOTLINKO[/][magenta]TLINKOTLINKOTL[/]",
        "[magenta]KOTLINKO[/][yellow]TLIN[/][blue]K[/][magenta]OTLINKOTLINKOTLIN[/]",
        "[magenta]KOTLINKOTL[/][blue]INKOT[/][magenta]LINKOTLINKOTLINKO[/]",
        "[magenta]KOTLINKO[/][blue]TLINKOTLI[/][magenta]NKOTLINKOTLINKOTL[/]",
        "[magenta]KOTLIN[/][blue]KOTLINKOTLINK[/][magenta]OTLINKOTLINKOTLIN[/]",
        "[magenta]KOTL[/][blue]INKOTLINKOTLINKOT[/][magenta]LINKOTLINKOTLINKO[/]",
        "[magenta]KO[/][blue]TLINKOTLINKOTLINKOTLI[/][magenta]NKOTLINKOTLINKOTL[/]",
    ],
    "Lua": [
        "[white]                 -- --[/]",
        "[white]         --                 --[/][blue] @@@@[/]",
        "[white]      --      [/][blue]@@@@@@@@@@@     @@@@@@[/]",
        "[blue]           @@@@@@@@@@@@@@@@@   @@@@[/]",
        "[white]  --     [/][blue]@@@@@@@@@@@@@@[/][white]@@@@[/][blue]@@@     [/][white]--[/]",
        "[white] --    [/][blue]@@@@@@@@@@@@@@@[/][white]@@@@@@[/][blue]@@@@    [/][white]--[/]",
        "[blue]      @@@@@@@@@@@@@@@@@[/][white]@@@@[/][blue]@@@@@@[/]",
        "[white]--   [/][blue]@@@[/][white]@@[/][blue]@@@@@@@@@@@@@@@@@@@@@@@@   [/][white]--[/]",
        "[white]--   [/][blue]@@@[/][white]@@[/][blue]@@@@@@[/][white]@@[/][blue]@@[/][white]@@[/][blue]@@[/][white]@@@@@@[/][blue]@@@@   [/][white]--[/]",
        "[blue]     @@@[/][white]@@[/][blue]@@@@@@[/][white]@@[/][blue]@@[/][white]@@[/][blue]@[/][white]@@[/][blue]@@@[/][white]@@[/][blue]@@@@[/]",
        "[white]--   [/][blue]@@@[/][white]@@[/][blue]@@@@@@[/][white]@@[/][blue]@@[/][white]@@[/][blue]@@@[/][white]@@@@@[/][blue]@@@@   [/][white]--[/]",
        "[white]--   [/][blue]@@@[/][white]@@[/][blue]@@@@@@[/][white]@@[/][blue]@@[/][white]@@[/][blue]@[/][white]@@@[/][blue]@@[/][white]@@[/][blue]@@@@   [/][white]--[/]",
        "[blue]      @@[/][white]@@@@@@@[/][blue]@[/][white]@@@@@@[/][blue]@[/][white]@@@@@@@@[/][blue]@@[/]",
        "[white] --    [/][blue]@@@@@@@@@@@@@@@@@@@@@@@@@    [/][white]--[/]",
        "[white]  --     [/][blue]@@@@@@@@@@@@@@@@@@@@@     [/][white]--[/]",
        "[blue]           @@@@@@@@@@@@@@@@@[/]",
        "[white]      --      [/][blue]@@@@@@@@@@@      [/][white]--[/]",
        "[white]         --                 --[/]",
        "[white]                 -- --[/]",
    ],
    "Markdown": [
        "[white]#######  [/][red] ,#####. .#####.[/]",
        "[white]  ###    [/][red]########.########[/]",
        "[white]  ###    [/][red]#################[/]",
        "[white]  ###    [/][red]`###############'[/]",
        "[white]  ###    [/][red] `#############'[/]",
        "[white]  ###    [/][red]   `#########'[/]",
        "[white]  ###    [/][red]     `#####'[/]",
        "[white]#######  [/][red]       `#'[/]",
        "[white][/]",
        "[white]####     ####     ###[/]",
        "[white]#####   #####     ###[/]",
        "[white]######.######     ###[/]",
        "[white]### ##### ###     ###[/]",
        "[white]###  ###  ###   #######[/]",
        "[white]###   #   ###    #####[/]",
        "[white]###       ###     ###[/]",
        "[white]###       ###      #[/]",
    ],
    "Nim": [
        "[yellow]                   ++[/]",
        "[yellow]       ++        ++++++        ++[/]",
        "[yellow]      ++++++++++++++++++++++++++++[/]",
        "[yellow]     ++++++++++++++++++++++++++++++[/]",
        "[yellow]++  ++++++++++++++++++++++++++++++++  ++[/]",
        "[yellow] ++++++++++++++++++++++++++++++++++++++[/]",
        "[yellow]  +++++++++++              +++++++++++[/]",
        "[yellow]   ++++++++                  ++++++++[/]",
        "[yellow]    +++++                      +++++[/]",
        "[white] ?   [/][yellow]++                          ++   [/][white]?[/]",
        "[white]  ??             ??????             ??[/]",
        "[white]   ???         ??????????         ???[/]",
        "[white]    ????     ??????????????     ????[/]",
        "[white]     ??????????????????????????????[/]",
        "[white]      ????????????????????????????[/]",
        "[white]       ??????????????????????????[/]",
        "[white]         ??????????????????????[/]",
        "[white]           ??????????????????[/]",
    ],
    "OCaml": [
        "[yellow]///////////////////////////////////////[/]",
        "[yellow]///////////////////////////////////////[/]",
        "[yellow]///////////////////////////////////////[/]",
        "[yellow]///////////////////////////////////////[/]",
        "[yellow]///////////////////////////////////////[/]",
        "[yellow]///   \\\\////    \\\\///////////////////////[/]",
        "[yellow]//      //      /////////     .////////[/]",
        "[yellow]/                ///////         \\\\/////[/]",
        "[yellow]                  /////      //////////[/]",
        "[yellow]                            ///////////[/]",
        "[yellow]                           ////////////[/]",
        "[yellow]  //                    ///////////////[/]",
        "[yellow] /////////   ///   ////////////////////[/]",
        "[yellow]/////////  //////  ////////////////////[/]",
        "[yellow]////////  ///////  ////////////////////[/]",
        "[yellow]///////  ////////  ////////////////////[/]",
        "[yellow]//////  /////////  ////////////////////[/]",
    ],
    "Perl": [
        "[cyan]                  ######[/]",
        "[cyan]    ###         #########[/]",
        "[cyan] ########      ##########[/]",
        "[cyan]#########     ############[/]",
        "[cyan]   ######   ###############[/]",
        "[cyan]  ####### ##################[/]",
        "[cyan]  ####### ###################[/]",
        "[cyan]  ############################[/]",
        "[cyan]  #############################[/]",
        "[cyan]  ########################### ##[/]",
        "[cyan]    ######################### ##[/]",
        "[cyan]     ###################  ### #[/]",
        "[cyan]          ##### #### ###  ### #[/]",
        "[cyan]          ####  #### ###   ##[/]",
        "[cyan]          ####  ###  ###    #[/]",
        "[cyan]           ##  ###   ###    #[/]",
        "[cyan]           ##   ##   ##     #[/]",
        "[cyan]           ##    #   #      #[/]",
        "[cyan]           #       ##       #[/]",
        "[cyan]           #       # #      #[/]",
        "[cyan]           #     ### ##     ##[/]",
        "[cyan]          ##[/]",
    ],
    "Python": [
        "[blue]               =========[/]",
        "[blue]            ===============[/]",
        "[blue]           =================[/]",
        "[blue]          ===  ==============[/]",
        "[blue]          ===================[/]",
        "[blue]                   ==========[/]",
        "[blue]   ========================== [/][yellow]=======[/]",
        "[blue] ============================ [/][yellow]========[/]",
        "[blue]============================= [/][yellow]=========[/]",
        "[blue]============================ [/][yellow]==========[/]",
        "[blue]========================== [/][yellow]============[/]",
        "[blue]============ [/][yellow]==========================[/]",
        "[blue]========== [/][yellow]============================[/]",
        "[blue]========= [/][yellow]=============================[/]",
        "[blue] ======== [/][yellow]============================[/]",
        "[blue]  ======= [/][yellow]==========================[/]",
        "[yellow]          ==========[/]",
        "[yellow]          ===================[/]",
        "[yellow]          ==============  ===[/]",
        "[yellow]           =================[/]",
        "[yellow]            ===============[/]",
        "[yellow]               =========[/]",
    ],
    "Ruby": [
        "[red]                -+sdmhmMMhyhNMMddm`[/]",
        "[red]            .smdy+:`  `-smmNy/    :h\\[/]",
        "[red]          -yNs.          mmhmo.    Md[/]",
        "[red]        -hNo`           oM- .oNh:  :s[/]",
        "[red]      :dm+`            .Ns    `/dmo.d[/]",
        "[red]     +Mo`              hN        yMMM[/]",
        "[red]   `sN/              /dMmsssoo++///NM[/]",
        "[red]  `hN-             +md/sM.        hNM[/]",
        "[red] .dm.            +mh:  .Ns      .dm+M[/]",
        "[red] +My          .oNy-     sM.    :Nd.+M[/]",
        "[red] +MM+     .:/sNd-       .Ns   sNo  sM[/]",
        "[red]`+MyMyhdddysmMoydmhs+:smdsM.+Nh-   hN[/]",
        "[red]`+M.MM:`   -Mo           hMNm/     md[/]",
        "[red]`+M  hm.   dm`         `+Nmdm+     My[/]",
        "[red]`/M:  md` /M/        -sNy:  -yNs. .Mo[/]",
        "[red] `Nh   Nh`Nh      :smd+.      .sNyoM/[/]",
        "[red]   `h:mh:MmNss:+sdNds:-::///++oosyN-[/]",
    ],
    "Rust": [
        "[red]                 R RR RR[/]",
        "[red]              R RRRRRRRR R          R[/]",
        "[red] R RR       R RRRRRRRRRRRRR R      RR[/]",
        "[red]rR RRR    R RRRRRRRRRRRRRRRRR R   RRR R[/]",
        "[red]RRR RR   RRRRRRRRRRRRRRRRRRRRRRR  RRRRR[/]",
        "[red] RRRRR  RRRRRRRRRRRRRRRRRRRRRRRR  RRRR[/]",
        "[red]  RRR RRRRRRRRRRRRRRRRRRRRRRRRRRRR RR[/]",
        "[red]    R  RRRRRRRRRR[/][white]=  [/][red]RR[/][white] = [/][red]RRRRRRRRRRR[/]",
        "[red]     RRRRRRRRRRRR[/][white]=  [/][red]RR[/][white] = [/][red]RRRRRRRRRR[/]",
        "[red]      RRRRRRRRRRR   RR   RRRRRRRRRR[/]",
        "[red]     RR==RRRRRRRRRRRRRRRRRRRRRR===RR[/]",
        "[red]     RR =  ==RRRRRRR  RRRRRR==  = RR[/]",
        "[red]      RR =     ===========     = RR[/]",
        "[red]       RR                        R[/]",
        "[red]        R                       R[/]",
        "[red]         R[/]",
    ],
    "Scala": [
        "[red]                        +[/]",
        "[red]                      +++[/]",
        "[red]          +++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++[/][red]-------[/]",
        "[red]+++[/][red]-------------------[/][red]+++[/]",
        "[red]        ---[/][red]++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++[/][red]-------[/]",
        "[red]+++[/][red]-------------------[/][red]+++[/]",
        "[red]        ---[/][red]++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++++++++++++[/]",
        "[red]+++++++++++++++[/]",
        "[red]+++[/]",
    ],
    "Shell": [
        "[white]             _._[/]",
        "[white]         _.-'   '-._[/]",
        "[white]     _.-'           '-._[/]",
        "[white] _.-'                   '-._[/]",
        "[white]|                        _,-|[/]",
        "[white]|                    _,-'+++|[/]",
        "[white]|                _,-'+++++++|[/]",
        "[white]|             ,-'+++++++++++|[/]",
        "[white]|             |++++ ++++++++|[/]",
        "[white]|             |+++   +++++++|[/]",
        "[white]|             |++  +++++++++|[/]",
        "[white]|             |++++  +++[/][green]**[/][white]++|[/]",
        "[white]|             |++   ++[/][green]**[/][white]++++|[/]",
        "[white]'-,_          |+++ ++++++_,-'[/]",
        "[white]    '-,_      |++++++_,-'[/]",
        "[white]        '-,_  |++_,-'[/]",
        "[white]            '-|-'[/]",
    ],
    "Svelte": [
        "[red]SSSSSSSSSSSSSSSSSS[/][white]sssssssssss[/][red]SSSSSSSS[/]",
        "[red]SSSSSSSSSSSSSSS[/][white]sssssssssssssssss[/][red]SSSSS[/]",
        "[red]SSSSSSSSSSS[/][white]sssssssssss[/][red]SSSS[/][white]ssssssss[/][red]SSS[/]",
        "[red]SSSSSSSS[/][white]ssssssssss[/][red]SSSSSSSSSSS[/][white]sssssss[/][red]S[/]",
        "[red]SSSSS[/][white]sssssssss[/][red]SSSSSSSSSSSSSSSSS[/][white]sssss[/][red]S[/]",
        "[red]SSS[/][white]ssssssss[/][red]SSSSSSSSSS[/][white]sssss[/][red]SSSSSS[/][white]ssss[/][red]S[/]",
        "[red]S[/][white]sssssss[/][red]SSSSSSSSSS[/][white]sssssssss[/][red]SSSSS[/][white]ssss[/][red]S[/]",
        "[red]S[/][white]sssss[/][red]SSSSSSSSS[/][white]sssssssssssssssssssss[/][red]S[/]",
        "[red]S[/][white]sssss[/][red]SSSSSS[/][white]ssssssss[/][red]SSSSSS[/][white]ssssssssss[/][red]S[/]",
        "[red]S[/][white]sssss[/][red]SSSSS[/][white]ssssss[/][red]SSSSSSSSSSSS[/][white]ssssss[/][red]SS[/]",
        "[red]S[/][white]sssss[/][red]SSSSSSSSSSSSSSSSSSSSSSSSS[/][white]sssss[/][red]S[/]",
        "[red]SS[/][white]ssssss[/][red]SSSSSSSSSSSS[/][white]ssssss[/][red]SSSSS[/][white]sssss[/][red]S[/]",
        "[red]S[/][white]ssssssssss[/][red]SSSSSS[/][white]ssssssss[/][red]SSSSSS[/][white]sssss[/][red]S[/]",
        "[red]S[/][white]sssssssssssssssssssss[/][red]SSSSSSSSS[/][white]sssss[/][red]S[/]",
        "[red]S[/][white]ssss[/][red]SSSSS[/][white]sssssssss[/][red]SSSSSSSSSS[/][white]ssssss[/][red]SS[/]",
        "[red]S[/][white]ssss[/][red]SSSSSS[/][white]sssss[/][red]SSSSSSSSSS[/][white]ssssssss[/][red]SSS[/]",
        "[red]S[/][white]sssss[/][red]SSSSSSSSSSSSSSSSS[/][white]sssssssss[/][red]SSSSS[/]",
        "[red]S[/][white]sssssss[/][red]SSSSSSSSSSS[/][white]ssssssssss[/][red]SSSSSSSS[/]",
        "[red]SSS[/][white]ssssssss[/][red]SSSS[/][white]sssssssssss[/][red]SSSSSSSSSSS[/]",
        "[red]SSSSS[/][white]sssssssssssssssss[/][red]SSSSSSSSSSSSSSS[/]",
        "[red]SSSSSSSS[/][white]sssssssssss[/][red]SSSSSSSSSSSSSSSSSS[/]",
    ],
    "Swift": [
        "[red]                         :[/]",
        "[red]                          ::[/]",
        "[red]                           :::[/]",
        "[red]          :                ::::[/]",
        "[red]     :     :                ::::[/]",
        "[red]      :     ::              :::::[/]",
        "[red]       ::    :::             :::::[/]",
        "[red]        :::    :::           ::::::[/]",
        "[red]          :::   :::          :::::::[/]",
        "[red]           ::::  ::::        :::::::[/]",
        "[red]            :::::::::::      ::::::::[/]",
        "[red]              :::::::::::   :::::::::[/]",
        "[red]               ::::::::::::::::::::::[/]",
        "[red]                :::::::::::::::::::::[/]",
        "[red]                  :::::::::::::::::::[/]",
        "[red]:                   :::::::::::::::::[/]",
        "[red] ::                   ::::::::::::::[/]",
        "[red]   ::::              ::::::::::::::::[/]",
        "[red]    ::::::::::::::::::::::::::::::::::[/]",
        "[red]      :::::::::::::::::::::::::::::::::[/]",
        "[red]        :::::::::::::::::::::::::::::::[/]",
        "[red]          ::::::::::::::::::::::   :::::[/]",
        "[red]             .::::::::::::::.         ::[/]",
        "[red][/]",
    ],
    "TypeScript": [
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTS[/][white]TSTSTSTSTSTSTS[/][cyan]TSTS[/][white]TSTSTS[/][cyan]TSTSTS[/]",
        "[cyan]TSTSTSTS[/][white]TSTSTSTSTSTSTS[/][cyan]TS[/][white]TSTSTSTSTS[/][cyan]TSTS[/]",
        "[cyan]TSTSTSTSTSTST[/][white]STST[/][cyan]STSTSTS[/][white]TSTST[/][cyan]TSTSTSTST[/]",
        "[cyan]TSTSTSTSTSTST[/][white]STST[/][cyan]STSTSTST[/][white]STSTS[/][cyan]TSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTST[/][white]STST[/][cyan]STSTSTSTST[/][white]STSTS[/][cyan]TSTSTS[/]",
        "[cyan]TSTSTSTSTSTST[/][white]STST[/][cyan]STSTSTSTSTST[/][white]STSTS[/][cyan]TSTS[/]",
        "[cyan]TSTSTSTSTSTST[/][white]STST[/][cyan]STSTSTSTSTSTS[/][white]TSTST[/][cyan]TST[/]",
        "[cyan]TSTSTSTSTSTST[/][white]STST[/][cyan]STSTSTST[/][white]STSTSTSTST[/][cyan]STS[/]",
        "[cyan]TSTSTSTSTSTST[/][white]STST[/][cyan]STSTSTSSTS[/][white]TSTSTS[/][cyan]TSTST[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
        "[cyan]TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS[/]",
    ],
    "Vue": [
        "[green]VUE[/][blue]\\\\\\\\\\                /////[/][green]VUE[/]",
        "[green] VUE[/][blue]\\\\\\\\\\              /////[/][green]VUE[/]",
        "[green]  VUE[/][blue]\\\\\\\\\\            /////[/][green]VUE[/]",
        "[green]   VUE[/][blue]\\\\\\\\\\          /////[/][green]VUE[/]",
        "[green]    VUE[/][blue]\\\\\\\\\\        /////[/][green]VUE[/]",
        "[green]     VUE[/][blue]\\\\\\\\\\      /////[/][green]VUE[/]",
        "[green]      VUE[/][blue]\\\\\\\\\\    /////[/][green]VUE[/]",
        "[green]       VUE[/][blue]\\\\\\\\\\  /////[/][green]VUE[/]",
        "[green]        VUE[/][blue]\\\\\\\\\\/////[/][green]VUE[/]",
        "[green]         VUE[/][blue]\\\\\\\\////[/][green]VUE[/]",
        "[green]          VUE[/][blue]\\\\\\///[/][green]VUE[/]",
        "[green]           VUE[/][blue]\\\\//[/][green]VUE[/]",
        "[green]            VUE[/][blue]||[/][green]VUE[/]",
        "[green]             VUEVUE[/]",
        "[green]              VUEV[/]",
    ],
    "Zig": [
        "[yellow]                                     z[/]",
        "[yellow]                                  zzz[/]",
        "[yellow]                             zzzzzz[/]",
        "[yellow]zzzzzzzzzzz  zzzzzzzzzzzzzzzzzzzz  zzz[/]",
        "[yellow]zzzzzzzzz  zzzzzzzzzzzzzzzzzzzz  zzzzz[/]",
        "[yellow]zzzzzzz  zzzzzzzzzzzzzzzzzzzz  zzzzzzz[/]",
        "[yellow]zzzzz                zzzzzz      zzzzz[/]",
        "[yellow]zzzzz              zzzzzz        zzzzz[/]",
        "[yellow]zzzzz            zzzzzz          zzzzz[/]",
        "[yellow]zzzzz          zzzzzz            zzzzz[/]",
        "[yellow]zzzzz        zzzzzz              zzzzz[/]",
        "[yellow]zzzzz      zzzzzz                zzzzz[/]",
        "[yellow]zzzzzzz  zzzzzzzzzzzzzzzzzzzz  zzzzzzz[/]",
        "[yellow]zzzzz  zzzzzzzzzzzzzzzzzzzz  zzzzzzzzz[/]",
        "[yellow]zzz  zzzzzzzzzzzzzzzzzzzz  zzzzzzzzzzz[/]",
        "[yellow]   zzzzzz[/]",
        "[yellow] zzz[/]",
        "[yellow]z[/]",
    ],
    "default": [
        "[dim]██████████[/]",
        "[dim]██[/]  [white]<>[/]  [dim]██[/]",
        "[dim]██[/]      [dim]██[/]",
        "[dim]██[/]      [dim]██[/]",
        "[dim]██████████[/]",
    ],
}


def image_to_ascii(image_path: Path, width: int = 20, height: int = 10) -> list[str]:
    """Convert an image to ASCII art with colors."""
    try:
        from PIL import Image
    except ImportError:
        return []

    try:
        img = Image.open(image_path)
    except Exception:
        return []

    # Resize maintaining aspect ratio (chars are ~2x taller than wide)
    aspect = img.height / img.width
    new_height = int(width * aspect * 0.5)
    new_height = min(new_height, height)
    img = img.resize((width, new_height), Image.Resampling.LANCZOS)

    # Convert to RGB if needed
    if img.mode != "RGB":
        img = img.convert("RGB")

    # ASCII chars from dark to light
    chars = " .:-=+*#%@"

    lines = []
    for y in range(img.height):
        line = ""
        for x in range(img.width):
            r, g, b = img.getpixel((x, y))
            # Luminance
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            char_idx = int(lum * (len(chars) - 1))
            char = chars[char_idx]

            # Convert RGB to Rich color
            line += f"[rgb({r},{g},{b})]{char}[/]"
        lines.append(line)

    return lines


def get_repo_icon() -> Optional[Path]:
    """Find icon.png in repo root."""
    root = get_repo_root()
    icon_names = ["icon.png", "logo.png", "icon.jpg", "logo.jpg", "icon.svg"]
    for name in icon_names:
        path = root / name
        if path.exists():
            return path
    return None


def get_ascii_art(loc_by_lang: Counter) -> list[str]:
    """Get ASCII art - from icon.png or language."""
    # Try custom icon first
    icon = get_repo_icon()
    if icon and icon.suffix.lower() in [".png", ".jpg", ".jpeg"]:
        art = image_to_ascii(icon, width=24, height=12)
        if art:
            return art

    # Fall back to language ASCII
    if loc_by_lang:
        top_lang = loc_by_lang.most_common(1)[0][0]
        return LANG_ASCII.get(top_lang, LANG_ASCII["default"])

    return LANG_ASCII["default"]


# Language detection by file extension
LANG_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".fish": "Shell",
    ".pl": "Perl",
    ".r": "R",
    ".R": "R",
    ".scala": "Scala",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".fs": "F#",
    ".clj": "Clojure",
    ".vim": "Vim Script",
    ".el": "Emacs Lisp",
    ".dart": "Dart",
    ".zig": "Zig",
    ".nim": "Nim",
    ".v": "V",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".sql": "SQL",
    ".dockerfile": "Dockerfile",
}

# Colors for languages (Rich styles)
LANG_COLORS = {
    "Python": "yellow",
    "JavaScript": "yellow",
    "TypeScript": "blue",
    "Go": "cyan",
    "Rust": "red",
    "C": "blue",
    "C++": "magenta",
    "Java": "red",
    "Kotlin": "magenta",
    "Swift": "red",
    "Ruby": "red",
    "Shell": "green",
    "HTML": "red",
    "CSS": "blue",
    "Vue": "green",
    "Markdown": "white",
}


def is_git_repo() -> bool:
    """Check if we're in a git repo."""
    result = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def get_repo_root() -> Path:
    """Get the repo root path."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True
    )
    return Path(result.stdout.strip())


def get_repo_name() -> str:
    """Get the repo name."""
    return get_repo_root().name


def get_remote_url() -> Optional[str]:
    """Get the origin remote URL."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        url = result.stdout.strip()
        # Clean up SSH URLs
        if url.startswith("git@"):
            url = url.replace(":", "/").replace("git@", "https://")
        if url.endswith(".git"):
            url = url[:-4]
        return url
    return None


def get_current_branch() -> str:
    """Get current branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def get_head_commit() -> str:
    """Get the HEAD commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def get_commit_count() -> int:
    """Get total number of commits."""
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True, text=True
    )
    return int(result.stdout.strip()) if result.returncode == 0 else 0


def get_contributors() -> list[tuple[str, int]]:
    """Get list of contributors with commit counts."""
    result = subprocess.run(
        ["git", "shortlog", "-sn", "--all", "--no-merges"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []

    contributors = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        match = re.match(r"\s*(\d+)\s+(.+)", line)
        if match:
            count, name = int(match.group(1)), match.group(2)
            contributors.append((name, count))

    return contributors


def get_first_commit_date() -> Optional[str]:
    """Get the date of the first commit."""
    result = subprocess.run(
        ["git", "log", "--reverse", "--format=%ai", "-1"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        date_str = result.stdout.strip()[:10]
        return date_str
    return None


def get_last_commit_date() -> Optional[str]:
    """Get the date of the last commit."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ai"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        date_str = result.stdout.strip()[:10]
        return date_str
    return None


def get_repo_age() -> str:
    """Calculate repo age from first commit."""
    first = get_first_commit_date()
    if not first:
        return "unknown"

    try:
        first_date = datetime.strptime(first, "%Y-%m-%d")
        diff = datetime.now() - first_date

        if diff.days < 30:
            return f"{diff.days} days"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''}"
        else:
            years = diff.days // 365
            months = (diff.days % 365) // 30
            if months > 0:
                return f"{years}y {months}mo"
            return f"{years} year{'s' if years > 1 else ''}"
    except ValueError:
        return first


def get_license() -> Optional[str]:
    """Detect license from LICENSE file."""
    root = get_repo_root()
    license_files = ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"]

    for name in license_files:
        path = root / name
        if path.exists():
            content = path.read_text(errors="ignore")[:500].lower()

            if "mit license" in content or "permission is hereby granted" in content:
                return "MIT"
            elif "apache license" in content:
                return "Apache 2.0"
            elif "gnu general public license" in content:
                if "version 3" in content:
                    return "GPL-3.0"
                elif "version 2" in content:
                    return "GPL-2.0"
                return "GPL"
            elif "bsd" in content:
                if "3-clause" in content or "three-clause" in content:
                    return "BSD-3-Clause"
                elif "2-clause" in content or "two-clause" in content:
                    return "BSD-2-Clause"
                return "BSD"
            elif "mozilla public license" in content:
                return "MPL-2.0"
            elif "unlicense" in content or "public domain" in content:
                return "Unlicense"
            elif "isc license" in content:
                return "ISC"

            return "Custom"

    return None


def get_pending_changes() -> tuple[int, int, int]:
    """Get pending changes (added, deleted, files changed)."""
    result = subprocess.run(
        ["git", "diff", "--shortstat"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return 0, 0, 0

    text = result.stdout.strip()
    files = added = deleted = 0

    # Parse "3 files changed, 10 insertions(+), 5 deletions(-)"
    if "file" in text:
        match = re.search(r"(\d+) file", text)
        if match:
            files = int(match.group(1))
    if "insertion" in text:
        match = re.search(r"(\d+) insertion", text)
        if match:
            added = int(match.group(1))
    if "deletion" in text:
        match = re.search(r"(\d+) deletion", text)
        if match:
            deleted = int(match.group(1))

    return added, deleted, files


def get_latest_version() -> Optional[str]:
    """Get latest version tag."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def get_last_change_relative() -> str:
    """Get relative time since last commit."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ar"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"


def get_repo_size() -> tuple[str, int]:
    """Get repo size and file count."""
    root = get_repo_root()

    # Get file count from git
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True, cwd=root
    )
    file_count = len(result.stdout.strip().split("\n")) if result.returncode == 0 else 0

    # Calculate size
    total_size = 0
    for rel_path in result.stdout.strip().split("\n"):
        if not rel_path:
            continue
        path = root / rel_path
        if path.exists() and path.is_file():
            try:
                total_size += path.stat().st_size
            except OSError:
                pass

    # Format size
    if total_size >= 1024 * 1024 * 1024:
        size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GiB"
    elif total_size >= 1024 * 1024:
        size_str = f"{total_size / (1024 * 1024):.2f} MiB"
    elif total_size >= 1024:
        size_str = f"{total_size / 1024:.2f} KiB"
    else:
        size_str = f"{total_size} B"

    return size_str, file_count


def get_most_changed_file() -> Optional[tuple[str, int]]:
    """Get the file with most recent changes (churn)."""
    result = subprocess.run(
        ["git", "log", "--format=", "--name-only", "-20"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None

    files = [f for f in result.stdout.strip().split("\n") if f.strip()]
    if not files:
        return None

    counter = Counter(files)
    most_common = counter.most_common(1)
    if most_common:
        path, count = most_common[0]
        # Shorten path if too long
        if len(path) > 25:
            path = "…/" + path.split("/")[-1]
        return path, count

    return None


def get_head_refs() -> str:
    """Get HEAD with branch refs."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%D"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        refs = result.stdout.strip()
        # Clean up refs
        refs = refs.replace("HEAD -> ", "").replace("origin/", "")
        parts = [r.strip() for r in refs.split(",")]
        # Deduplicate
        seen = set()
        unique = []
        for p in parts:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        return ", ".join(unique[:3])
    return ""


def count_lines_of_code() -> tuple[int, Counter]:
    """Count lines of code by language. Returns (total, by_language)."""
    root = get_repo_root()
    by_lang = Counter()

    # Use git ls-files to only count tracked files
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True, text=True, cwd=root
    )
    if result.returncode != 0:
        return 0, by_lang

    for rel_path in result.stdout.strip().split("\n"):
        if not rel_path:
            continue

        path = root / rel_path
        if not path.exists() or not path.is_file():
            continue

        ext = path.suffix.lower()
        # Also check for files like Dockerfile
        if ext == "" and path.name.lower() == "dockerfile":
            ext = ".dockerfile"

        if ext not in LANG_EXTENSIONS:
            continue

        lang = LANG_EXTENSIONS[ext]

        try:
            with open(path, "r", errors="ignore") as f:
                lines = sum(1 for _ in f)
                by_lang[lang] += lines
        except (OSError, IOError):
            pass

    return sum(by_lang.values()), by_lang


def get_branch_count() -> int:
    """Get number of local branches."""
    result = subprocess.run(
        ["git", "branch", "--list"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return len([b for b in result.stdout.strip().split("\n") if b.strip()])
    return 0


def get_tag_count() -> int:
    """Get number of tags."""
    result = subprocess.run(
        ["git", "tag", "--list"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return len([t for t in result.stdout.strip().split("\n") if t.strip()])
    return 0


def format_number(n: int) -> str:
    """Format number with k/m suffix."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def build_language_bar(loc_by_lang: Counter, total_loc: int, width: int = 40) -> str:
    """Build a horizontal language bar like onefetch."""
    bar = ""
    top_langs = loc_by_lang.most_common(6)

    for lang, count in top_langs:
        pct = (count / total_loc) if total_loc > 0 else 0
        chars = max(1, int(pct * width))
        color = LANG_COLORS.get(lang, "white")
        bar += f"[{color}]{'█' * chars}[/]"

    return bar


def display_info() -> None:
    """Display all repo info as a card with ASCII art and columns."""
    from rich.table import Table as RichTable

    repo_name = get_repo_name()
    branch = get_current_branch()
    head = get_head_commit()
    head_refs = get_head_refs()
    remote = get_remote_url()

    # Gather stats
    commits = get_commit_count()
    contributors = get_contributors()
    license_name = get_license()
    created = get_repo_age()
    num_branches = get_branch_count()
    tags = get_tag_count()
    total_loc, loc_by_lang = count_lines_of_code()
    added, deleted, pending_files = get_pending_changes()
    version = get_latest_version()
    last_change = get_last_change_relative()
    size_str, file_count = get_repo_size()
    churn = get_most_changed_file()

    # Get ASCII art
    ascii_art = get_ascii_art(loc_by_lang)

    console.print()

    # Build info lines (right side)
    info_lines = []

    # HEAD line
    head_line = f"[dim]HEAD[/]        [yellow]{head}[/]"
    if head_refs:
        head_line += f" [dim]({head_refs})[/]"
    info_lines.append(head_line)

    # Branches/tags
    branch_parts = []
    if num_branches > 0:
        branch_parts.append(f"{num_branches} branch{'es' if num_branches > 1 else ''}")
    if tags > 0:
        branch_parts.append(f"{tags} tag{'s' if tags > 1 else ''}")
    if branch_parts:
        info_lines.append(f"[dim]Refs[/]        {', '.join(branch_parts)}")

    # Pending changes
    if added > 0 or deleted > 0:
        pending = f"[dim]Pending[/]     [green]+{added}[/] [red]-{deleted}[/]"
        info_lines.append(pending)

    # Version
    if version:
        info_lines.append(f"[dim]Version[/]     [cyan]{version}[/]")

    # Created & Last change
    info_lines.append(f"[dim]Created[/]     {created} ago")
    info_lines.append(f"[dim]Changed[/]     {last_change}")

    # Commits
    info_lines.append(f"[dim]Commits[/]     [green]{commits}[/]")

    # Lines of code + Size
    info_lines.append(f"[dim]Lines[/]       {format_number(total_loc)}  [dim]Size[/] {size_str}")

    # Languages (inline)
    if loc_by_lang:
        top_langs = loc_by_lang.most_common(3)
        lang_parts = []
        for lang, count in top_langs:
            pct = (count / total_loc) * 100
            color = LANG_COLORS.get(lang, "white")
            lang_parts.append(f"[{color}]●[/]{lang} {pct:.0f}%")
        info_lines.append(f"[dim]Lang[/]        {' '.join(lang_parts)}")

    # Authors (inline)
    if contributors:
        auth_parts = []
        for name, cnt in contributors[:2]:
            pct = (cnt / commits) * 100 if commits > 0 else 0
            auth_parts.append(f"[green]{name[:12]}[/] {pct:.0f}%")
        info_lines.append(f"[dim]Authors[/]     {' '.join(auth_parts)}")

    # License
    if license_name:
        info_lines.append(f"[dim]License[/]     [green]{license_name}[/]")

    # Pad ASCII art and info to same length
    max_rows = max(len(ascii_art), len(info_lines))
    while len(ascii_art) < max_rows:
        ascii_art.append("")
    while len(info_lines) < max_rows:
        info_lines.append("")

    # Create layout with ASCII art on left, info on right
    layout = RichTable(box=None, show_header=False, padding=(0, 2), expand=False)
    layout.add_column("Art", width=42, no_wrap=True)
    layout.add_column("Info", no_wrap=True)

    for art, info in zip(ascii_art, info_lines):
        layout.add_row(art, info)

    # Add URL at bottom
    subtitle = f"[dim]{remote}[/]" if remote else None

    console.print(Panel(
        layout,
        title=f"[bold cyan]{repo_name}[/]",
        subtitle=subtitle,
        border_style="cyan",
        padding=(0, 1),
    ))
    console.print()


def main(argv: list[str] = None) -> int:
    """Main entry point for iskra info."""
    if not is_git_repo():
        console.print("[red]Error:[/] Not in a git repository")
        return 1

    display_info()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
