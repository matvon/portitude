#!/usr/bin/python
import curses
import curses.panel
import portage
import inspect
import re

###############################################################################
An adaptation of aptitude to the gentoo portage package management sytem,
based on ncurses.
###############################################################################
class Pkg:
  def __init__(self, name, inWorld):
    self.name    = name
    self.inWorld = inWorld

###############################################################################

class PkgDatabase:
  def __init__(self):
    self.vartree   = portage.db[portage.root]['vartree']
    self.porttree  = portage.db[portage.root]['porttree']
    self.varPkgDb = {}
    self.worldList = open('/var/lib/portage/world').read().splitlines()

    listPropKey   = ["DESCRIPTION", "CATEGORY","BUILD_TIME","KEYWORDS","HOMEPAGE","FEATURES",\
                 "DEPEND", "RDEPEND", "IUSE", "USE"]

    for cpvName in self.vartree.getallcpv():
      category, pkgName, version, rev = portage.catpkgsplit(cpvName)  
      cpName = category +'/'+ pkgName
      self.varPkgDb[cpName] = {}
      self.varPkgDb[cpName][version] = {}
      inWorld = cpName in self.worldList
      self.varPkgDb[cpName][version]['inWorld'] = inWorld
      listPropVal = self.vartree.dbapi.aux_get(cpvName, listPropKey)
      cpt = 0
      for propKey in listPropKey:
        self.varPkgDb[cpName][version][propKey] = listPropVal[cpt]
        cpt += 1
    self.varList = list(self.varPkgDb.keys())
  def isInWorld(self, cpName):
      if self.varPkgDb[cpName]:
        for version in self.varPkgDb[cpName]:
          if self.varPkgDb[cpName][version]['inWorld']:
            return True
      return False

###############################################################################
class MainScreen:
  def __init__(self, screen, pkgDb):
    self.win      = screen
    self.pkgDb     = pkgDb
    self.dbg       = open('portitude.dbg','w')
    self.win.keypad(1)
    curses.noecho()
    curses.cbreak()
    curses.curs_set(0)
    curses.start_color()

    self.maxY, self.maxX = screen.getmaxyx()
    curses.init_pair(1,curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2,curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(3,curses.COLOR_BLUE, curses.COLOR_WHITE)

    self.highlightStyle = curses.color_pair(1)
    self.worldStyle     = curses.color_pair(2)
    self.hWorldStyle    = curses.color_pair(3)
    self.normalStyle    = curses.A_NORMAL
    
    self.top = TopWin(self, int(self.maxY/2),self.maxX);
    self.bot = BotWin(self, self.maxY - self.top.maxY, self.maxX, self.top.maxY)
    #self.helpPanel = Panel(30,30,30,30,"Portitude")

  def runMenu(self):
    self.bot.setPkg(self.top.displayList[0])
    while 1:
      self.top.show()
      self.bot.show()
      c = self.win.getch()
      if c == ord('q'):
        break        #Exit the programm
      elif c == curses.KEY_UP:
        self.previousLine()
      elif c == curses.KEY_DOWN:
        self.nextLine()
      elif c == curses.KEY_PPAGE:
        self.previousPage()
      elif c == curses.KEY_NPAGE:
        self.nextPage()
      elif c == curses.KEY_LEFT:
        self.bot.previous()
      elif c == curses.KEY_RIGHT:
        self.bot.next()
      elif c == 10: #curses.KEY_ENTER:
        self.bot.showSelected()
      elif c == ord('w'):  
        self.top.switchList()

      #elif c == ord('h'):
      #  self.helpPanel.show()
      self.win.clear()
      self.top.win.noutrefresh()
      self.bot.win.noutrefresh()
      #self.helpPanel.noutrefresh()a
      #self.helpPanel.flushPanel()
  def previousLine(self):
    if self.top.selectedLine > 0:
      self.top.selectedLine  -= 1 
    elif self.top.selectedLine == 0 and self.top.firstPkgIndex > 0:
      self.top.firstPkgIndex -= 1 
    self.bot.setPkg(self.top.getCurrentPkg())

  def nextLine(self):
    maxLine = self.top.maxY
    pkgNumber = len(self.top.displayList)
    self.dbg.write(str(maxLine))
    if self.top.selectedLine  < maxLine - 1:  #Not in last line
      self.top.selectedLine += 1
    elif self.top.selectedLine == maxLine - 1\
    and self.top.firstPkgIndex < pkgNumber - maxLine:
      self.top.firstPkgIndex += 1
    self.bot.setPkg(self.top.getCurrentPkg())
    
  def nextPage(self):
    maxLine = self.top.maxY
    pkgNumber = len(self.top.displayList)
    if self.top.firstPkgIndex + 2 * (maxLine - 1)< pkgNumber:
      self.top.selectedLine = maxLine - 1 
      self.top.firstPkgIndex += maxLine - 1
    else:
      self.top.firstPkgIndex = pkgNumber - maxLine
      self.top.selectedLine = maxLine - 1
    self.bot.setPkg(self.top.getCurrentPkg())
  
  def previousPage(self):
    maxLine = self.top.maxY
    if self.top.firstPkgIndex > maxLine:
      self.top.firstPkgIndex -= maxLine - 1
    else:
      self.top.firstPkgIndex = 0
    self.top.selectedLine = 0  
    self.bot.setPkg(self.top.getCurrentPkg())
###############################################################################    
class TopWin:
  selectedLine   = 0
  firstPkgIndex  = 0
  def __init__(self, main, maxY, maxX):
    self.maxY = maxY
    self.maxX = maxX
    self.main = main
    self.win = main.win.subwin(maxY, maxX, 0, 0)
    self.displayList   = self.main.pkgDb.varList 
    self.showWorld     = False
  def show(self):
    line = 0;
    currentKeys = self.displayList[self.firstPkgIndex : self.firstPkgIndex + self.maxY]
    for cpName in currentKeys:
      multiVersionPkgList = self.main.pkgDb.varPkgDb[cpName]
      pkg = multiVersionPkgList[multiVersionPkgList.keys()[0]]
      inWorld = pkg['inWorld']
      #Define style
      if line == self.selectedLine:
        if inWorld:
          textStyle = self.main.hWorldStyle
        else:    
          textStyle = self.main.highlightStyle
      else:
        if inWorld:
          textStyle = self.main.worldStyle
        else: 
          textStyle = self.main.normalStyle
      self.main.win.addstr(line,0,str(cpName),textStyle)
      line += 1 
  def getCurrentPkg(self):
    return self.displayList[self.firstPkgIndex + self.selectedLine]
  def switchList(self):
    self.showWorld = not self.showWorld
    self.firstPkgIndex = 0
    self.selectedLine  = 0
    if self.showWorld:
      self.displayList = self.main.pkgDb.worldList
    else:
      self.displayList = self.main.pkgDb.varList

###############################################################################    
class BotWin:
  pkgIndex = 0
  botSelectedPkg   = ""
  def __init__(self, main, maxY, maxX, posY):
    self.maxY = maxY
    self.maxX = maxX
    self.main = main
    self.win = main.win.subwin(maxY, maxX, posY, 0)
    self.content = ""
    self.pkgList = []

  def getCpFromFullName(self,fullName):
    cpvPkgNamePattern = "[0-9a-zA-Z-]*/[0-9a-zA-Z_]*([-][a-zA-Z][0-9a-zA-Z_]*)*"
    cpName = re.search(cpvPkgNamePattern, fullName).group(0)
    return cpName
  
  def showSelected(self):
    cpName = self.getCpFromFullName(self.botSelectedPkg)
    self.setPkg(cpName)

  def previous(self):   
    if self.pkgIndex > 0: self.pkgIndex -= 1

  def next(self):
    if self.pkgIndex < len(self.pkgList) - 1:
      self.pkgIndex += 1

  def setPkg(self,pkgName):
    toShow = ["DESCRIPTION", "CATEGORY","BUILD_TIME","KEYWORDS","HOMEPAGE","FEATURES",\
              "DEPEND", "RDEPEND", "IUSE", "USE"]
    toLook = ["DEPEND", "RDEPEND"]
    self.pkgList = []
    self.content = "PACKAGE : " + pkgName + "\n"
    self.pkgIndex = 0
    
    try:
      multiVerPkg = self.main.pkgDb.varPkgDb[pkgName]
    except:
      self.main.dbg.write("Package not found : " + pkgName)
      return
    pkg = multiVerPkg[multiVerPkg.keys()[0]]
    
    self.toLookString = "" 
    for key in toShow:
      try:
        if key in toLook:
            self.toLookString += key + " : " + pkg[key] + "\n"
        else:
          self.content += key + " : " + pkg[key] + "\n"
      except:
         self.main.dbg.write("Error getting info on : "+ pkgName + '\n')
    fullPkgPattern = "[\-!<>=0-9a-zA-Z.]*/[\-0-9a-zA-Z.:_\*]*"
    pattern  = re.compile(" " + fullPkgPattern)
    self.pkgList    = tuple(re.finditer(pattern, self.toLookString))

  def show(self):
    self.win.border(' ',' ',0,' ',curses.ACS_HLINE,curses.ACS_HLINE,' ',' ')
    self.win.move(1,0)
    try:
      self.win.addstr(self.content)
      if len(self.pkgList) != 0:
        end = 0
        cpt = 0
        for pkg in self.pkgList:
          begin = pkg.start()  #Update begin index
          self.win.addstr(self.toLookString[end : begin]) #Display from old end to new begin
          end  = pkg.end()     #Update end index
          self.botSelectedPkg = self.toLookString[begin+1 : end]
          try:
            inWorld = self.main.pkgDb.isInWorld(self.getCpFromFullName(pkg.group(0)))
          except:
            inWorld = False
          if self.pkgIndex == cpt:
            textStyle = self.main.highlightStyle
          elif inWorld:
            textStyle = self.main.worldStyle
          else:
            textStyle = self.main.normalStyle
          self.win.addstr(" ")  
          self.win.addstr(self.toLookString[begin +  1 : end],textStyle)
          cpt += 1
        self.win.addstr(self.toLookString[end :])
    except curses.error as e:
        self.main.dbg.write("Text clipping occurs for package "\
                       + self.botSelectedPkg + "\n")
    
###############################################################################
class Panel:
  def __init__(self,x,y,sx,sy,msg):
    self.panelWin = curses.newwin(x,y,sx,sy)
    self.panel    = curses.panel.new_panel(self.panelWin)
    self.panelWin.addstr(msg)
    self.panel.top()
    self.panel.show()
  def flushPanel(self):
    curses.panel.update_panels()
    curses.doupdate()

###############################################################################

def main(stdscr):
  pkgDb     = PkgDatabase()
  screen = MainScreen(stdscr, pkgDb)
  screen.runMenu()

curses.wrapper(main)

