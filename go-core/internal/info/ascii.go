// Package info provides repository statistics like onefetch.
package info

import (
	"github.com/charmbracelet/lipgloss"
)

// Language colors (Lip Gloss)
var LangColors = map[string]lipgloss.Color{
	"Python":     lipgloss.Color("226"), // Yellow
	"JavaScript": lipgloss.Color("226"), // Yellow
	"TypeScript": lipgloss.Color("39"),  // Blue
	"Go":         lipgloss.Color("86"),  // Cyan
	"Rust":       lipgloss.Color("196"), // Red
	"C":          lipgloss.Color("39"),  // Blue
	"C++":        lipgloss.Color("201"), // Magenta
	"Java":       lipgloss.Color("196"), // Red
	"Kotlin":     lipgloss.Color("201"), // Magenta
	"Swift":      lipgloss.Color("196"), // Red
	"Ruby":       lipgloss.Color("196"), // Red
	"Shell":      lipgloss.Color("82"),  // Green
	"HTML":       lipgloss.Color("196"), // Red
	"CSS":        lipgloss.Color("39"),  // Blue
	"Vue":        lipgloss.Color("82"),  // Green
	"Markdown":   lipgloss.Color("255"), // White
	"Lua":        lipgloss.Color("39"),  // Blue
	"Elixir":     lipgloss.Color("201"), // Magenta
	"Haskell":    lipgloss.Color("201"), // Magenta
	"Scala":      lipgloss.Color("196"), // Red
	"Clojure":    lipgloss.Color("82"),  // Green
	"Dart":       lipgloss.Color("39"),  // Blue
	"Zig":        lipgloss.Color("226"), // Yellow
	"Nim":        lipgloss.Color("226"), // Yellow
}

// ASCII art for programming languages (inspired by onefetch)
// Using simple ANSI color codes that work with Lip Gloss
var LangASCII = map[string][]string{
	"Go": {
		"           --==============--",
		"  .-==-.===oooo=oooooo=ooooo===--===-",
		" .==  =o=oGGGGGGo=oo=oGGGGGGGG=o=  oo-",
		" -o= oo=G .=GGGGGo=o== .=GGGGG=ooo o=-",
		"  .-=oo=o==oGGGGG=oo=oooGGGGGo=oooo.",
		"   -ooooo=oooooo=.   .==ooo==oooooo-",
		"   -ooooooooooo====_====ooooooooooo=",
		"   -oooooooooooo==#.#==ooooooooooooo",
		"   -ooooooooooooo=#.#=oooooooooooooo",
		"   .oooooooooooooooooooooooooooooooo.",
		"    oooooooooooooooooooooooooooooooo.",
		"  ..oooooooooooooooooooooooooooooooo..",
		"-=o-=ooooooooooooooooooooooooooooooo-oo.",
		".=- oooooooooooooooooooooooooooooooo-.-",
		"   .oooooooooooooooooooooooooooooooo-",
		"   -oooooooooooooooooooooooooooooooo-",
		"   -oooooooooooooooooooooooooooooooo-",
		"   -oooooooooooooooooooooooooooooooo-",
		"   .oooooooooooooooooooooooooooooooo",
		"    =oooooooooooooooooooooooooooooo-",
		"    .=oooooooooooooooooooooooooooo-",
		"      -=oooooooooooooooooooooooo=.",
		"     =oo====oooooooooooooooo==-oo=-",
		"    .-==-    .--=======---     .==-",
	},
	"Python": {
		"               =========",
		"            ===============",
		"           =================",
		"          ===  ==============",
		"          ===================",
		"                   ==========",
		"   ========================== =======",
		" ============================ ========",
		"============================= =========",
		"============================ ==========",
		"========================== ============",
		"============ ==========================",
		"========== ============================",
		"========= =============================",
		" ======== ============================",
		"  ======= ==========================",
		"          ==========",
		"          ===================",
		"          ==============  ===",
		"           =================",
		"            ===============",
		"               =========",
	},
	"JavaScript": {
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
		"JSJSJSJSJSJSJSJSJ    SJSJS      JSJSJS",
		"JSJSJSJSJSJSJSJSJ    SJS          JSJS",
		"JSJSJSJSJSJSJSJSJ    SJS     JSJSJSJSJ",
		"JSJSJSJSJSJSJSJSJ    SJSJ     SJSJSJSJ",
		"JSJSJSJSJSJSJSJSJ    SJSJSJ     SJSJSJ",
		"JSJSJSJSJSJSJSJSJ    SJSJSJSJ     JSJS",
		"JSJSJSJSJSJSJSJSJ    SJSJSJSJS     JSJ",
		"JSJSJSJSJS     JS    JSJS          JSJ",
		"JSJSJSJSJSJ          SJSJSJ      SJSJS",
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
		"JSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJSJS",
	},
	"TypeScript": {
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
		"TSTSTSTS TSTSTSTSTSTSTS TSTS TSTSTS TSTSTS",
		"TSTSTSTS TSTSTSTSTSTSTS TS TSTSTSTSTS TSTS",
		"TSTSTSTSTSTST STST STSTSTS TSTST TSTSTSTST",
		"TSTSTSTSTSTST STST STSTSTST STSTS TSTSTSTS",
		"TSTSTSTSTSTST STST STSTSTSTST STSTS TSTSTS",
		"TSTSTSTSTSTST STST STSTSTSTSTST STSTS TSTS",
		"TSTSTSTSTSTST STST STSTSTSTSTSTS TSTST TST",
		"TSTSTSTSTSTST STST STSTSTST STSTSTSTST STS",
		"TSTSTSTSTSTST STST STSTSTSSTS TSTSTS TSTST",
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
		"TSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTSTS",
	},
	"Rust": {
		"                 R RR RR",
		"              R RRRRRRRR R          R",
		" R RR       R RRRRRRRRRRRRR R      RR",
		"rR RRR    R RRRRRRRRRRRRRRRRR R   RRR R",
		"RRR RR   RRRRRRRRRRRRRRRRRRRRRRR  RRRRR",
		" RRRRR  RRRRRRRRRRRRRRRRRRRRRRRR  RRRR",
		"  RRR RRRRRRRRRRRRRRRRRRRRRRRRRRRR RR",
		"    R  RRRRRRRRRR=  RR = RRRRRRRRRRR",
		"     RRRRRRRRRRRR=  RR = RRRRRRRRRR",
		"      RRRRRRRRRRR   RR   RRRRRRRRRR",
		"     RR==RRRRRRRRRRRRRRRRRRRRRR===RR",
		"     RR =  ==RRRRRRR  RRRRRR==  = RR",
		"      RR =     ===========     = RR",
		"       RR                        R",
		"        R                       R",
		"         R",
	},
	"Ruby": {
		"                -+sdmhmMMhyhNMMddm",
		"            .smdy+:  -smmNy/    :h\\",
		"          -yNs.          mmhmo.    Md",
		"        -hNo           oM- .oNh:  :s",
		"      :dm+            .Ns    /dmo.d",
		"     +Mo              hN        yMMM",
		"   sN/              /dMmsssoo++///NM",
		"  hN-             +md/sM.        hNM",
		" .dm.            +mh:  .Ns      .dm+M",
		" +My          .oNy-     sM.    :Nd.+M",
		" +MM+     .:/sNd-       .Ns   sNo  sM",
		"+MyMyhdddysmMoydmhs+:smdsM.+Nh-   hN",
		"+M.MM:   -Mo           hMNm/     md",
		"+M  hm.   dm         +Nmdm+     My",
		"/M:  md /M/        -sNy:  -yNs. .Mo",
		" Nh   NhNh      :smd+.      .sNyoM/",
		"   h:mh:MmNss:+sdNds:-::///++oosyN-",
	},
	"C": {
		"                 ++++++",
		"              ++++++++++++",
		"          ++++++++++++++++++++",
		"       ++++++++++++++++++++++++++",
		"    ++++++++++++++++++++++++++++++++",
		" +++++++++++++************+++++++++++++",
		"+++++++++++******************++++++++;;;",
		"+++++++++**********************++;;;;;;;",
		"++++++++*********++++++******;;;;;;;;;;;",
		"+++++++********++++++++++**;;;;;;;;;;;;;",
		"+++++++*******+++++++++;;;;;;;;;;;;;;;;;",
		"+++++++******+++++++;;;;;;;;;;;;;;;;;;;;",
		"+++++++*******+++:::::;;;;;;;;;;;;;;;;;;",
		"+++++++********::::::::::**;;;;;;;;;;;;;",
		"++++++++*********::::::******;;;;;;;;;;;",
		"++++++:::**********************::;;;;;;;",
		"+++::::::::******************::::::::;;;",
		" :::::::::::::************:::::::::::::",
		"    ::::::::::::::::::::::::::::::::",
		"       ::::::::::::::::::::::::::",
		"          ::::::::::::::::::::",
		"              ::::::::::::",
		"                 ::::::",
	},
	"Shell": {
		"             _._",
		"         _.-'   '-._",
		"     _.-'           '-._",
		" _.-'                   '-._",
		"|                        _,-|",
		"|                    _,-'+++|",
		"|                _,-'+++++++|",
		"|             ,-'+++++++++++|",
		"|             |++++ ++++++++|",
		"|             |+++   +++++++|",
		"|             |++  +++++++++|",
		"|             |++++  +++**++|",
		"|             |++   ++**++++|",
		"'-,_          |+++ ++++++_,-'",
		"    '-,_      |++++++_,-'",
		"        '-,_  |++_,-'",
		"            '-|-'",
	},
	"Lua": {
		"                 -- --",
		"         --                 -- @@@@",
		"      --      @@@@@@@@@@@     @@@@@@",
		"           @@@@@@@@@@@@@@@@@   @@@@",
		"  --     @@@@@@@@@@@@@@@@@@@@     --",
		" --    @@@@@@@@@@@@@@@@@@@@@@@    --",
		"      @@@@@@@@@@@@@@@@@@@@@@@@@",
		"--   @@@@@@@@@@@@@@@@@@@@@@@@@@@   --",
		"--   @@@@@@@@@@@@@@@@@@@@@@@@@@@   --",
		"     @@@@@@@@@@@@@@@@@@@@@@@@@@@",
		"--   @@@@@@@@@@@@@@@@@@@@@@@@@@@   --",
		"--   @@@@@@@@@@@@@@@@@@@@@@@@@@@   --",
		"      @@@@@@@@@@@@@@@@@@@@@@@@@@",
		" --    @@@@@@@@@@@@@@@@@@@@@@@    --",
		"  --     @@@@@@@@@@@@@@@@@@@     --",
		"           @@@@@@@@@@@@@@@@@",
		"      --      @@@@@@@@@@@      --",
		"         --                 --",
		"                 -- --",
	},
	"Haskell": {
		"yyyyyy xxxxxx",
		" yyyyyy xxxxxx",
		"  yyyyyy xxxxxx",
		"   yyyyyy xxxxxx",
		"    yyyyyy xxxxxx yyyyyyyyyy",
		"     yyyyyy xxxxxx yyyyyyyyy",
		"      yyyyyy xxxxxx",
		"     yyyyyy xxxxxxxx yyyyyyy",
		"    yyyyyy xxxxxxxxxx yyyyyy",
		"   yyyyyy xxxxxxxxxxxx",
		"  yyyyyy xxxxxx  xxxxxx",
		" yyyyyy xxxxxx    xxxxxx",
		"yyyyyy xxxxxx      xxxxxx",
	},
	"Scala": {
		"                        +",
		"                      +++",
		"          +++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++-------",
		"+++-------------------+++",
		"        ---++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++-------",
		"+++-------------------+++",
		"        ---++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++++++++++++",
		"+++++++++++++++",
		"+++",
	},
	"default": {
		"██████████",
		"██  <>  ██",
		"██      ██",
		"██      ██",
		"██████████",
	},
}

// GetASCIIArt returns the ASCII art for a language
func GetASCIIArt(lang string) []string {
	if art, ok := LangASCII[lang]; ok {
		return art
	}
	return LangASCII["default"]
}

// GetLangColor returns the Lip Gloss color for a language
func GetLangColor(lang string) lipgloss.Color {
	if color, ok := LangColors[lang]; ok {
		return color
	}
	return lipgloss.Color("255") // White default
}
