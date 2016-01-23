import datetime
import gtk
import random
from pyscrabble.game.pieces import *
from pyscrabble.gui.pieces import *
from pyscrabble.constants import *
from pyscrabble.gtkconstants import *
from pyscrabble import gtkutil
from pyscrabble import util
from pyscrabble import exceptions
from twisted.internet import reactor
try:
    set
except NameError:
    from sets import Set as set

import sys
sys.path.append("../../../platform/build/bindings/python/")
sys.path.append("../../../platform/bindings/python/")
from libpydiamond import *
import ReactiveManager
import gobject
from pyscrabble.game.game import *
from pyscrabble import constants
import os
import codecs
import threading


class GameFrame(gtk.Frame):
    '''
    Game Frame.
    
    The GameFrame displays the gameboard and the players that are involved in the current game.
    
    Players can::
        - Start the game
        - Leave the game
        - Pause/Unpause the game.
    
    '''
    
    
    def __init__(self, client, main, gameId, username, spectating, options):
        '''
        Initialize the game frame
        
        @param client: ScrabbleClient instance
        @param main: Main Window
        @param gameId: Game ID
        @param spectating: True if the user is spectating
        @param options: Game options
        '''
        
        gtk.Frame.__init__(self)
        
        self.username = username.encode("utf-8")
        
        # callback to socket client
        self.client = client
        self.client.addGameWindow(self, gameId)
        self.mainwindow = main
        
        self.currentGameId = gameId
        self.currentGame = ScrabbleGame(gameId)
        self.player = Player(username, gameId)
        self.prevLetters = []
        self.recentMoves = []
        self.hideTradeButton = False
        
        self.spectating = spectating
        self.gameOptions = {OPTION_CENTER_TILE: True, 52: 'en', OPTION_SHOW_COUNT: True}
        
        self.letters = [] # User letter list
        self.onBoard = Move() # Letters on board for current move
        self.tileTips = gtk.Tooltips()
        
        main = gtk.VBox( False, 5 )
        
        top = gtk.HBox( False, 5 )
        top.pack_start(self.getGrid(), False, False, 20)
        top.pack_start(self.createUsersWindow(), False, False, 0)
        
        main.pack_start(top, False, False, 20)
        main.pack_start(self.initUserLetters(), False, False, 0)
        
        resources = manager.ResourceManager()
        self.dicts = {}
        dir = resources["resources"][constants.DICT_DIR].path
        for lang in os.listdir( dir ):
            if not lang.islower(): continue # Avoids CVS directories
            self.dicts[lang] = set()
            for file in os.listdir( os.path.join(dir, lang) ):
                if not file.islower(): continue # Avoids CVS directories
                path = os.path.join(dir, lang, file)
                
                f = codecs.open(path, encoding='utf-8', mode='rb')
                lines = f.read().split()
                f.close()
                
                l = []
                for line in lines:
                    l.append( line.upper() )
                x = set( l )
                
                self.dicts[lang] = self.dicts[lang].union(x)
        
        self.gameLetters = []
        for i in range(0, 7):
            gl = GameLetter(None, self.letterBox)
            self.letterBox.pack_start(gl)
            self.gameLetters.append(gl)
        self.letterBox.show_all()
        
        self.wasPlayerTurn = None
        
        self.set_border_width( 10 )
        self.add( main )
        self.show_all()
        
        # Hide the toolbar if the user is a spectator
        if self.spectating:
            self.toolBar.hide()
        
        self.userView.columns_autosize()
                
        ReactiveManager.add(self.drawScreen)
    
    def destroy(self):
        ReactiveManager.remove(self.drawScreen)
        gtk.Frame.destroy(self)
    
    def drawScreen(self):
        self.drawLetters()
        self.drawBoard()
        self.drawUserList()
        self.drawUI()
        
    def drawBoard(self):
        for tile in self.board.tiles.values():
            letter = tile.getLetter()
            gobject.idle_add(tile.set_label, letter)
            gobject.idle_add(tile.updateBackground, letter)
    
    def drawLetters(self):
        if (self.currentGame.started.Value()):
            letters = self.player.getLetters()
            gobject.idle_add(self.showLetters, letters)
    
    def drawUserList(self):
        users = []
        players = self.currentGame.getPlayers()
        for player in players:
            users.append(PlayerInfo(player.getUsername(), player.getScore(), len(player.getLetters())))
        
        gobject.idle_add(self.userList.clear)
        for playerInfo in users:
            gobject.idle_add(self.appendWrapper, (playerInfo.name, str(playerInfo.score), playerInfo.time, str(playerInfo.numLetters)) )
    
    def appendWrapper(self, tuple):
        self.userList.append(tuple)
    
    def drawUI(self):
        currentPlayerName = self.currentGame.getCurrentPlayer().getUsername()
        started = self.currentGame.started.Value()
        thisPlayerName = self.player.getUsername()
        gobject.idle_add(self.drawUIHelper, started, thisPlayerName, currentPlayerName)
    
    def drawUIHelper(self, started, thisPlayerName, currentPlayerName):
        if started:
            self.startButton.hide()
            self.saveButton.set_sensitive(True)
        
        isPlayerTurn = (currentPlayerName == thisPlayerName)
        
        if self.wasPlayerTurn == None or isPlayerTurn != self.wasPlayerTurn:
            self.mainwindow.setCurrentTurn(self.currentGameId, isPlayerTurn)
            self.wasPlayerTurn = isPlayerTurn
        
        if isPlayerTurn:
            self.okButton.set_sensitive(True)
            self.passButton.set_sensitive(True)
            if self.hideTradeButton == False:
                self.tradeButton.set_sensitive(True)
            self.cancelButton.set_sensitive(True)
            self.shuffleButton.set_sensitive(True)
            
            self.board.activate()
            
        else:
            self.okButton.set_sensitive(False)
            self.passButton.set_sensitive(False)
            self.tradeButton.set_sensitive(False)
            self.cancelButton.set_sensitive(False)
            self.shuffleButton.set_sensitive(True)
            
            self.board.deactivate()
                        
            if currentPlayerName is not None:
                sel = self.userView.get_selection()
                model = self.userView.get_model()
            
                it = model.get_iter_first()
                while ( it != None ):
                    name = model.get_value(it, 0)
                    if (name == currentPlayerName):
                        if self.gameOptions.has_key(OPTION_TIMED_GAME) or self.gameOptions.has_key(OPTION_MOVE_TIME):
                            path = model.get_path(it)
                        #sel.select_iter(it)
                        break
                    it = model.iter_next(it)

    
    ### UI Creation ####
        
    def getLogWindow(self):
        '''
        Create the log window
        
        @return: ScrolledWindow containing the TextView
        '''
        
        self.notebook = gtk.Notebook()
        self.notebook.set_tab_pos( gtk.POS_TOP )
        
        self.logWindow = gtkutil.TaggableTextView(buffer=None)
        self.logWindow.set_editable( False )
        self.logWindow.set_cursor_visible( False )
        self.logWindow.set_wrap_mode( gtk.WRAP_WORD )
        self.logWindow.connect("drag-motion", self.dragMotion, True)
        self.logWindow.set_size_request( 400, 200 )
        
        window = gtk.ScrolledWindow()
        window.add( self.logWindow )
        window.set_policy( gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC )
        
        box = gtk.VBox(False, 2)
        box.pack_start(window, True, True, 0)
        
        self.notebook.append_page(box, gtk.Label(_("Chat")))
        self.notebook.append_page(self.getStatWindow(), gtk.Label(_("Info")))
        self.notebook.append_page(self.getSpecWindow(), gtk.Label(_("Spectators")))
        self.notebook.append_page(self.getOptionsWindow(), gtk.Label(_("Options")))
        if self.gameOptions[OPTION_SHOW_COUNT]:
            self.notebook.append_page(self.getDistributionWindow(), gtk.Label(_("Letter Distribution")))
        self.notebook.show_all()
        
        return self.notebook
    
    def getStatWindow(self):
        '''
        Retrieve statistics information window
        
        @return: gtk.TreeView
        '''
        
        self.statList = gtk.ListStore(str, str)
        view = gtk.TreeView( self.statList )
        view.set_headers_visible( False )
        
        col1 = gtk.TreeViewColumn(_('Name'))
        cell1 = gtk.CellRendererText()
        col1.pack_start(cell1, True)
        col1.add_attribute(cell1, 'text', 0)
        
        col2 = gtk.TreeViewColumn(_('Value'))
        cell2 = gtk.CellRendererText()
        col2.pack_start(cell2, True)
        col2.add_attribute(cell2, 'text', 1)
        
        view.append_column( col1 )
        view.append_column( col2 )
        
        return view
    
    def getDistributionWindow(self):
        '''
        Letter Distribution window
        
        @return: gtk.ScrolledWindow
        '''
        self.distributionList = gtk.ListStore(str, str)
        view = gtk.TreeView( self.distributionList )
        view.set_headers_visible( True )
        
        col1 = gtk.TreeViewColumn(_('Letter'))
        cell1 = gtk.CellRendererText()
        col1.pack_start(cell1, True)
        col1.add_attribute(cell1, 'text', 0)
        
        col2 = gtk.TreeViewColumn(_('# Remaining in bag'))
        cell2 = gtk.CellRendererText()
        col2.pack_start(cell2, True)
        col2.add_attribute(cell2, 'text', 1)
        
        view.append_column( col1 )
        view.append_column( col2 )
        
        window = gtk.ScrolledWindow()
        window.add( view )
        window.set_policy( gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC )
        
        return window
        
    
    def getSpecWindow(self):
        '''
        Retrieve spectators window
        
        @return: gtk.TreeView
        '''
        
        self.specList = gtk.ListStore(str)
        self.specView = gtk.TreeView( self.specList )
        self.specView.set_headers_visible( False )
        self.specView.connect("button-release-event", self.mainwindow.userListClicked_cb)
        self.specView.connect("button-press-event", self.mainwindow.userListClicked_cb)
        
        col1 = gtk.TreeViewColumn(_('Name'))
        cell1 = gtk.CellRendererText()
        col1.pack_start(cell1, True)
        col1.add_attribute(cell1, 'text', 0)
                
        self.specView.append_column( col1 )

        
        return self.specView
    
    def getOptionsWindow(self):
        '''
        Retrieve options window
        
        @return: gtk.TreeView
        '''
        
        box = gtk.VBox(False, 0)
        
        self.optionList = gtk.ListStore(str,str)
        self.optionView = gtk.TreeView( self.optionList )
        self.optionView.set_headers_visible( False )
        
        col1 = gtk.TreeViewColumn(_('Name'))
        cell1 = gtk.CellRendererText()
        col1.pack_start(cell1, True)
        col1.add_attribute(cell1, 'text', 0)
        col1.connect("notify::width", self.optionViewWidthChanged_cb, 0)
        
        col2 = gtk.TreeViewColumn(_('Value'))
        cell2 = gtk.CellRendererText()
        col2.pack_start(cell2, True)
        col2.add_attribute(cell2, 'text', 1)
        
        self.optionView.append_column( col1 )
        self.optionView.append_column( col2 )
        
        
        self.gameOptionModel = gtk.ListStore(str,bool)
        self.gameOptionView = gtk.TreeView( self.gameOptionModel )
        self.gameOptionView.set_headers_visible( False )
        
        col1 = gtk.TreeViewColumn(_('Name'))
        cell1 = gtk.CellRendererText()
        col1.pack_start(cell1, True)
        col1.add_attribute(cell1, 'text', 0)
        
        self.specEnabled = gtk.CellRendererToggle()
        self.specEnabled.set_property('activatable', True)
        self.specEnabled.connect("toggled", self.specEnabled_cb, True)
        self.specEnabled.set_property('xalign', 0.0)
        
        col2 = gtk.TreeViewColumn(_('Value'), self.specEnabled)
        col2.add_attribute(self.specEnabled, 'active', True)
        
        self.gameOptionView.append_column( col1 )
        self.gameOptionView.append_column( col2 )
        
        if not self.spectating:
            self.gameOptionModel.append( [_("Allow Spectators"),True] )        
            self.gameOptionModel.append( [_("Allow Spectator Chat"),True] )        


        self.gameOptionView.get_selection().connect("changed", lambda w,v: v.get_selection().unselect_all(), self.optionView)
        self.optionView.get_selection().connect("changed", lambda w,v: v.get_selection().unselect_all(), self.gameOptionView)
        
        box.pack_start(self.optionView, False, False, 0)
        box.pack_start(self.gameOptionView, True, True, 0)
        
        return box
        
        
    
    def initUserLetters(self):
        '''
        Initialize the users letter box
        
        @return: gtk.HBox that will hold users letters and action buttons
        '''
        
        box = gtk.HBox(False, 10)
        self.letterBox = gtk.HBox(False, 1)
        
        self.okButton = gtkutil.createToolButton(STOCK_SEND_MOVE, STOCK_SEND_MOVE)
        self.passButton = gtkutil.createToolButton(STOCK_PASS, STOCK_PASS)
        self.tradeButton = gtkutil.createToolButton(STOCK_TRADE_LETTERS, STOCK_TRADE_LETTERS)
        self.cancelButton = gtkutil.createToolButton(gtk.STOCK_CLEAR, None)
        self.shuffleButton = gtkutil.createToolButton(STOCK_SHUFFLE, STOCK_SHUFFLE)
        
        self.okButton.set_sensitive(False)
        self.passButton.set_sensitive(False)
        self.tradeButton.set_sensitive(False)
        self.cancelButton.set_sensitive(False)
        self.shuffleButton.set_sensitive(False)
        
        self.toolBar = gtk.Toolbar()
        self.toolBar.set_style(gtk.TOOLBAR_BOTH)
        self.toolBar.set_show_arrow(False)
        self.toolBar.set_icon_size(gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.toolBar.insert(self.okButton, 0)
        self.toolBar.insert(gtk.SeparatorToolItem(), 1)
        self.toolBar.insert(self.passButton, 2)
        self.toolBar.insert(gtk.SeparatorToolItem(), 3)
        self.toolBar.insert(self.tradeButton, 4)
        self.toolBar.insert(gtk.SeparatorToolItem(), 5)
        self.toolBar.insert(self.cancelButton, 6)
        self.toolBar.insert(gtk.SeparatorToolItem(), 7)
        self.toolBar.insert(self.shuffleButton, 8)
        
        self.okButton.connect("clicked", self.sendCurrentMove)
        self.passButton.connect("clicked", self.askPass)
        self.tradeButton.connect("clicked", self.tradeLetters)
        self.cancelButton.connect("clicked", self.clearCurrentMoveBackground)
        self.shuffleButton.connect('clicked', self.shuffleLetters_cb)
        
        t = gtk.VBox(False, 0)
        t.pack_start(self.letterBox, False, False, 0)
        box.pack_start(t, False, False, 10)
        box.pack_start(self.toolBar, False, False, 0)
        
        return box
        
        
    def createUsersWindow(self):
        '''
        Create TextView that shows users in the game and their scores.
        
        @return: gtk.VBox containing TextView of Users/Scores and action buttons
        '''
        
        vbox = gtk.VBox(False, 1)
        
        self.userList = gtk.ListStore(str, str, str, str)
        self.userView = gtk.TreeView( self.userList )
        self.userView.connect("button-release-event", self.mainwindow.userListClicked_cb)
        self.userView.connect("button-press-event", self.mainwindow.userListClicked_cb)
        
        col1 = gtk.TreeViewColumn(_('Player'))
        cell1 = gtk.CellRendererText()
        col1.pack_start(cell1, True)
        col1.add_attribute(cell1, 'text', 0)
        col1.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        
        col2 = gtk.TreeViewColumn(_('Score'))
        cell2 = gtk.CellRendererText()
        col2.pack_start(cell2, True)
        col2.add_attribute(cell2, 'text', 1)
        col2.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        
        col4 = gtk.TreeViewColumn(_('Letters left'))
        cell4 = gtk.CellRendererText()
        col4.pack_start(cell4, True)
        col4.add_attribute(cell4, 'text', 3)
        col4.set_visible(False)
        col4.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        
        self.userView.append_column( col1 )
        self.userView.append_column( col2 )
        self.userView.append_column( col4 )
        
        header = gtk.Label()
        s = _("Current Game")
        header.set_markup("<b><big>%s:</big></b>" % s)
        header.set_justify( gtk.JUSTIFY_LEFT )
        
        self.actionBox = gtk.HButtonBox()
        
        self.startButton = gtk.Button(label=_("Start Game"))
        self.saveButton = gtk.Button(label=_("Save Game"))
        self.saveButton.set_sensitive(False)
        leaveButton = gtk.Button(label=_("Leave Game"))
        
        self.startButton.connect("clicked", self.startGame)
        self.pauseHandlerId = self.saveButton.connect("clicked", self.doPauseGame)
        leaveButton.connect("clicked", self.askLeaveGame_cb)
        
        self.actionBox.add(self.startButton)
        self.actionBox.add(self.saveButton)
        self.actionBox.add(leaveButton)
        self.actionBox.set_layout( gtk.BUTTONBOX_START )
        
        vbox.pack_start(header, False, False, 1)
        vbox.pack_start(self.userView, False, False, 0)
        
        if not self.spectating:
            vbox.pack_start(self.actionBox, False, False, 0)
            
        vbox.pack_start(self.getLogWindow(), False, False, 7)
        
        exp = gtk.Expander()
        exp.add(vbox)
        exp.set_expanded(True)
        return exp
        
    
    # Create the gameboard
    def getGrid(self):
        '''
        Create the game board
        
        @return: The GameBoard
        '''
        
        
        self.board = GameBoard(self)
        
        # Create the blank board
        for y in range(15):
            for x in range(15):
                
                tile = GameTile(x,y, self)
                
                self.board.put(tile, x, y)
        
        return self.board
    
    
    # Trade letters in for new letters
    def tradeLettersBackground(self, button):
        threading.Thread(target=self.tradeLetters, args=(button)).start()
        
    def tradeLetters(self, button):
        '''
        Allow the user to trade letters in.  This counts as a turn
        
        @param button: Button that was clicked
        '''  
        
        DObject.TransactionBegin()
        
        l = []
        for letter in self.letterBox.get_children():
            if isinstance(letter, GameLetter):
                if letter.get_active():
                    l.append(letter.getLetter())
                    letter.set_active(False)
                
        if len(l) > 0:
            print "DEBUG TRADELETTERS"
            self.clearCurrentMove()
            print "player letters: " + repr(self.player.getLetters())
            self.player.removeLetters( l )
            print "list l is: " + repr(l)
            letters = self.currentGame.getLetters( self.player.getNumberOfLettersNeeded() )
            print "list letters is: " + repr(letters)
            self.player.addLetters( letters )
            self.currentGame.returnLetters( l )
            print "player letters: " + repr(self.player.getLetters())

            self.currentGame.resetPassCount()
            self.doGameTurn()
        else:
            self.error(util.ErrorMessage(_("Please Click on the Letters you wish to trade")))
            
        DObject.TransactionCommit()
    
    # Pause the game
    def doPauseGame(self, button):
        '''
        User action to Pause the game
        
        @param button: Button that was clicked
        '''
        self.client.pauseGame( self.currentGameId )
    
    # Unpause the game
    def doUnpauseGame(self, button):
        '''
        User action to Unpause the game
        
        @param button: Button that was clicked
        '''
        self.client.unPauseGame( self.currentGameId )
        
    
    # Start the game
    def startGame(self, button):
        threading.Thread(target=self.startGameHelper, args=(button)).start()
    
    def startGameHelper(self, button):
        '''
        User starts a game
        
        @param gameId: Game ID
        @param client: ScrabbleServer Protocol
        '''
        DObject.TransactionBegin()
        if self.username != self.currentGame.getCreator():
            gobject.idle_add(self.error, util.ErrorMessage(ServerMessage([NOT_CREATOR])))
            DObject.TransactionCommit()
            return
        
        if (self.currentGame.isStarted()):
            gobject.idle_add(self.error, util.ErrorMessage(ServerMessage([GAME_ALREADY_STARTED])))
            DObject.TransactionCommit()
            return

        self.currentGame.start()
        
        for player in self.currentGame.getPlayers():
            player.reset()
            letters = self.currentGame.getLetters( player.getNumberOfLettersNeeded() )
            player.addLetters(letters)
        
        #TODO
        #self.sendGameScores(game.getGameId())

        #TODO
        self.doGameTurn()
        DObject.TransactionCommit()
        #TODO
        #self.refreshGameList()
        
    def doGameTurn(self, wasUnpaused=False ):
        '''
        Turn control of the board to the next player in the game
        
        @param gameId: Game ID
        '''
        
        player = self.currentGame.getNextPlayer()
        
        if player is None:
            return
    
    def gameOver(self):
        '''
        Game over
        
        Notify the user and then disable the buttons
        '''
        p = gtkutil.Popup( title=self.currentGameId, text=_('Game over'))
        self.leaveGame(button=None, clientLeaveGame=False)
    
    # Leave a game
    def leaveGame(self, button, clientLeaveGame = True, disableChat = False):
        '''
        User action to leave the game
        
        @param button: Widget that was clicked
        @param clientLeaveGame: True if the client initiated the action to leave the game.  False if the server is booting the user.
        @param disableChat: Flag to disable chat
        '''
        
        # True if we want to initiate the disconnect.  False if the server boots us
        if clientLeaveGame:
            try:
                self.client.leaveGame( self.currentGameId )
            except KeyError: pass # Key error if the client has already removed the game.  This will be the case when the game is over
                
            self.mainwindow.removeGame(self.currentGameId)
            self.destroy()
        
        #self.toolBar.hide()
        self.okButton.set_sensitive(False)
        self.passButton.set_sensitive(False)
        self.tradeButton.set_sensitive(False)
        self.cancelButton.set_sensitive(False)
        self.shuffleButton.set_sensitive(False)
        
        self.actionBox.hide()
        if disableChat:
            self.gameEntry.hide()
            self.specEnabled.set_property('activatable', False)
        
        #Deactivate dragging on the letters
        #self.letterBox.foreach(lambda letter: letter.deactivate())
        self.board.deactivate()
        
        #TODO: verify that this is correct
        self.player.reset()
        #self.showLetters([])
    
    
    # Game state management methods added by Niel
    def addLetter(self, letter):
        '''
        @param letter: Letter to add to list of letters
        '''
        self.player.addLetters([letter])
        
    def removeLetter(self, letter):
        '''
        @param letter: Letter to remove from list of letters
        '''
        #letters = []
        #found = False
        #for _letter in self.letters:
        #    if letter == _letter and letter.isBlank() == _letter.isBlank():
        #        if not found:
        #            found = True
        #        else:
        #            letters.append( _letter )
        #    else:
        #        letters.append( _letter )        
        #self.letters = letters
        #self.showLetters(self.letters)
        self.player.removeLetters([letter])
        
    def registerMove(self, tile, x, y): 
        self.onBoard.addMove( tile.getLetter() ,x,y )
        
    def removeMove(self, tile, x, y):
        self.onBoard.removeMove( tile.getLetter(), x, y )
        
    def swapTiles(self, gTileA, gTileB):
        threading.Thread(target=self.swapTilesHelper, args=(gTileA, gTileB)).start()
        
    def swapTilesHelper(self, gTileA, gTileB):
        DObject.TransactionBegin()
        letterA = gTileA.getLetter()
        letterB = gTileB.getLetter()
        if letterA == None:
            self.removeMove(gTileB, gTileB.x, gTileB.y)
            gTileB.clear()
        else:
            self.removeMove(gTileA, gTileA.x, gTileA.y)
            self.removeMove(gTileB, gTileB.x, gTileB.y)
            gTileB.putLetter(letterA)
            self.registerMove(gTileB, gTileB.x, gTileB.y)

        gTileA.putLetter(letterB)
        self.registerMove(gTileA, gTileA.x, gTileA.y)
        DObject.TransactionCommit()
    
    def swapTileAndLetter(self, gTile, gLetter):
        threading.Thread(target=self.swapTileAndLetterHelper, args=(gTile, gLetter)).start()
        
    def swapTileAndLetterHelper(self, gTile, gLetter):
        DObject.TransactionBegin()
        origLetterLetter = gLetter.getLetter()
        origTileLetter = gTile.getLetter()
        
        if origLetterLetter == None:
            self.removeMove(gTile, gTile.x, gTile.y)
            self.addLetter(origTileLetter)
            gTile.clear()
        else:
            self.removeLetter(origLetterLetter)
            
            if gTile.getLetter() != None:
                self.removeMove(gTile, gTile.x, gTile.y)
                self.addLetter(origTileLetter)
        
            gTile.putLetter(origLetterLetter)
            self.registerMove(gTile, gTile.x, gTile.y)
        DObject.TransactionCommit()
        
    def putTileOnPlaceholder(self, gTile):
        DObject.TransactionBegin()
        self.removeMove(gTile, gTile.x, gTile.y)
        self.addLetter(gTile.getLetter())
        gTile.clear()
        DObject.TransactionCommit()
    
    
    def getNumOnBoardMoves(self):
        '''
        
        @return: Number of moves on the board
        '''
        return self.onBoard.length()
        
    
    def hasOnboardMove(self, x, y):
        '''
        Check if a we have a move at x,y on the board
        
        @param x:
        @param y:
        '''
        tile = self.board.get(x,y)
        if tile is not None:
            if tile.getLetter() is not None:
                return self.onBoard.contains(tile.getLetter(),x,y)
        return False
        
    
    # Callback to clear letters put on board
    def clearCurrentMoveBackground(self, event=None):
        threading.Thread(target=self.clearCurrentMoveBackgroundHelper, args=()).start()
    
    def clearCurrentMoveBackgroundHelper(self):
        DObject.TransactionBegin()
        self.clearCurrentMove()
        DObject.TransactionCommit()
        
    def clearCurrentMove(self):
        '''
        Callback to clear the current move off the board
        
        @param event:
        '''
        if not self.onBoard.isEmpty():
            for letter,x,y in self.onBoard.getTiles():
                #print 'Clearing %s %d,%d' % (letter,x,y)
                self.player.addLetters([letter])
                #t = GameTile(x,y,self)
                #t.activate()
                #self.board.put(t,x,y)
                t = self.board.get(x, y)
                t.clear()
            self.onBoard.clear()
    
    
    # Callback to send current move
    def sendCurrentMove(self, event = None):
        threading.Thread(target=self.sendCurrentMoveHelper, args=(event)).start()
        
    def sendCurrentMoveHelper(self, event = None):
        '''
        Send the current move on the board to the server
        
        @param event:
        '''
        
        DObject.TransactionBegin()
        
        if (self.isCurrentTurn() == False):
            gobject.idle_add(self.error, util.ErrorMessage(_("Its not your turn")))
            DObject.TransactionCommit()
            return
        
        if (not self.onBoard.isValid()):
            gobject.idle_add(self.error, util.ErrorMessage(_("Move is invalid")))
            DObject.TransactionCommit()
            return
        
        # Make sure the board has a letter in the center or one of the tiles in this move does
        if (self.board.isEmpty()):
            center = False
            for letter, x, y in self.onBoard.getTiles():
                if (x+1,y+1) in CENTER:
                    center = True
            if not center:
                gobject.idle_add(self.error, util.ErrorMessage(_("Move must cover center tile.")))
                DObject.TransactionCommit()
                return
            
        # Check for blanks
        for letter,x,y in self.onBoard.getTiles():
            if (letter.isBlank() and letter.getLetter() ==""):
                new = self.showBlankLetterDialog()
                if (new == ""): # new will be blank if the user cancels the dialog
                    DObject.TransactionCommit()
                    return
                else:
                    #print 'Blank set on %s' % str(id(letter))
                    letter.setLetter( new )
                    
                    # We need to check if the board is empty
                    # If it is, putting a Letter on the board will cause it not to be empty.
                    # If the board is set as not empty, and its the players firsrt move, the
                    # game will reject the move because it wont be touching any other tiles
                    #if self.board.isEmpty():
                        #self.board.putLetter(letter, x, y)
                        #self.board.empty = True
                    #else:
                        #self.board.putLetter(letter, x, y)
    
        try:
            moves = self.getMoves()
            self.gameSendMove(self.currentGameId, self.onBoard, moves)
            #self.client.sendMoves( self.currentGameId, moves, self.onBoard )
            #self.okButton.set_sensitive(False)
        except exceptions.MoveException, inst:
            gobject.idle_add(self.error, util.ErrorMessage(inst.message))
            
        DObject.TransactionCommit()
    
    # Player send move to game
    def gameSendMove(self, gameId, onboard, moves):
        '''
        User sends moves to the game
        
        @param gameId: Game ID
        @param onboard: Move containing letters put on the board
        @param moves: List of Moves formed
        '''
        
        game = ScrabbleGame(gameId)
        player = game.getPlayer( self.player )
        
        if not player == game.getCurrentPlayer():
            return
        
        if (game.isPaused()):
            gobject.idle_add(self.error, util.ErrorMessage(ServerMessage([MOVE_GAME_PAUSED])))
            return
        if (not game.isInProgress()):
            gobject.idle_add(self.error, util.ErrorMessage(ServerMessage([NOT_IN_PROGRESS])) )
            return
        
        # Validate word in dictionary and not on the board alread
        words = []
        for move in moves:
            word = util.getUnicode( move.getWord() )
            if word not in self.dicts[ 'en' ]:
                gobject.idle_add(self.error, util.ErrorMessage(ServerMessage([word, NOT_IN_DICT])) )
                return
            words.append( word )
        
        self.acceptMove()
        score = self.getMovesScore(game, moves)
        letters = self.getLettersFromMove(onboard)
        player.removeLetters( letters )
        player.addScore( score )
        
        self.removeModifiers(game, moves)
        
        game.addMoves(moves, player)
        
        game.resetPassCount()
        
        # If the player used all 7 of his/her letters, give them an extra 50
        if onboard.length() == 7:
            player.addScore( constants.BINGO_BONUS_SCORE )
            
            # If the player used all his/her letters and there are no more letters in the bag, the game is over
        if (len(player.getLetters()) == 0 and game.isBagEmpty()):
            
            # Subtract everyones letter points
            # Give points to the person who went out
            players = game.getPlayers()
            for p in players:
                if p == player: 
                    continue # Skip winner
                    
                letters = p.getLetters()
                for letter in letters:
                    p.addScore( letter.getScore() * -1 )
                    player.addScore( letter.getScore() )
            
            self.sendGameScores(game.getGameId())
            
            self.gameOver(game)
            return

        letters = game.getLetters( player.getNumberOfLettersNeeded() )
        if (len(letters) > 0):
            player.addLetters(letters)
            
        self.board.empty.Set(False)

        # Next player
        self.doGameTurn(gameId)
        
    # Get the letters from the moves
    def getLettersFromMove(self, move):
        '''
        Get the letters in a move
        
        @param move: Move
        @return: List of letters in C{move}
        '''
        
        letters = []
        
        for letter, x, y in move.getTiles():
            letters.append( letter.clone() )

        return letters
    
    # Get the score of the list of moves
    def getMovesScore(self, game, moves):
        '''
        Get the total score for a list of Moves
        
        @param game: ScrabbleGame
        @param moves: List of Moves
        @return: Total score for the list of Moves
        '''
        
        total = 0
        
        for move in moves:
            score = 0
            apply = 0
            modifier = constants.TILE_NORMAL
            m_x = -1
            m_y = -1
            for letter,x,y in move.getTiles():
                m = util.getTileModifier(x,y)
                if m in constants.LETTER_MODIFIERS and not game.hasUsedModifier((x,y)):
                    score = score + (m * letter.getScore())
                else:
                    score = score + letter.getScore()
    
                if (m >= modifier and not game.hasUsedModifier((x,y))):
                    modifier = m
                    if m in constants.WORD_MODIFIERS:
                        apply = apply + 1
                    m_x = x
                    m_y = y

            if modifier in constants.WORD_MODIFIERS and not game.hasUsedModifier((m_x,m_y)):
                
                if util.isCenter(m_x, m_y):
                    score = score * (modifier/2)
                else:
                    score = score * ((modifier/2) ** apply)
                
            move.setScore( score )
            total = total + score
        
        return total
    
    def removeModifiers(self, game, moves):
        '''
        Mark off modifiers that are used in this move
        
        @param game: Game
        @param moves: List of moves
        '''
        for move in moves:
            for letter,x,y in move.getTiles():
                m = util.getTileModifier(x,y)
                if m in constants.LETTER_MODIFIERS and not game.hasUsedModifier((x,y)):
                    game.addUsedModifier( (x,y) )
                if m in constants.WORD_MODIFIERS and not game.hasUsedModifier((x,y)):
                    game.addUsedModifier( (x,y) )
    
    # Button click to pass the move
    def passMove(self, event = None):
        '''
        Player passes his turn
        
        @param event:
        '''
        
        self.clearCurrentMove()    
        self.client.passMove( self.currentGameId )
    
    def getMoves(self):
        '''
        Gets the list of moves from the tiles on the board
        
        @return: List of Moves or None if the tiles on board do not form a valid move.
        '''
        
        moves = []
        
        if self.board.isEmpty():
            if not self.onBoard.isContinuous():
                #print 'empty board'
                raise exceptions.TilesNotConnectedException
        
        list = set()
        temp = self.onBoard.clone()
        for letter, x, y in temp.getTiles():
            _xs = self.board.getTilesAtX(x)
            for _l, _x, _y in _xs:
                list.add( (_l, _x, _y) )
            _ys = self.board.getTilesAtY(y)
            for _l, _x, _y in _ys:
                list.add( (_l, _x, _y) )
        
        groupx = {}
        groupy = {}
        for l, x, y in list:
            if (groupx.has_key(x)):
                groupx[x].append( (l,x,y) )
            else:
                groupx[x] = [ (l,x,y) ]
            
            if (groupy.has_key(y)):
                groupy[y].append( (l,x,y) )
            else:
                groupy[y] = [ (l,x,y) ]

        for _x in groupx.keys():
            if (len(groupx[_x]) > 1):
                m = Move()
                ms = []
                groupx[_x].sort( lambda (l1, x1, y1), (l2, x2, y2): y1-y2 )
                for l, x, y in groupx[_x]:
                    t = m.clone()
                    t.addMove(l.getLetter(), x, y)
                    if (t.isContinuous()):
                        m.addMove(l.getLetter(), x, y)
                    else:
                        ms.append(m)
                        m = Move()
                        m.addMove(l.getLetter(), x, y)
                ms.append(m)
                for _m in ms:
                    if (_m.hasCommonTile(self.onBoard) and _m.length() > 1 and _m.isContinuous()):
                        moves.append(_m)
        
        for _y in groupy.keys():
            if (len(groupy[_y]) > 1):
                m = Move()
                ms = []
                groupy[_y].sort( lambda (l1, x1, y1), (l2, x2, y2): x1-x2 )
                for l, x, y in groupy[_y]:
                    t = m.clone()
                    t.addMove(l.getLetter(), x, y)
                    if (t.isContinuous()):
                        m.addMove(l.getLetter(), x, y)
                    else:
                        ms.append(m)
                        m = Move()
                        m.addMove(l.getLetter(), x, y)
                ms.append(m)
                for _m in ms:
                    if (_m.hasCommonTile(self.onBoard) and _m.length() > 1 and _m.isContinuous()):
                        moves.append(_m)

        # Make sure that every letter in the "on board" tiles is represented in a word
        found = {}
        for letter,x,y in self.onBoard.getTiles():
            found[letter] = False
            for m in moves:
                if m.contains(letter,x,y):
                    found[letter] = True
        
        for val in found.itervalues():
            if val == False:
                raise exceptions.TilesNotConnectedException
        
        # Make sure that every move is touching the board
        if not self.board.isEmpty():
            for m in moves:
                if not self.board.moveTouching(m, self.onBoard):
                    raise exceptions.MoveNotTouchingException
        
        # If the tiles on the board are not continuous, make sure that one of the 
        # formed words contains all the tiles on board.  This prevents users
        # from placing disjointed words that still connect to an existing word:
        #         TESTING
        #        TO     ONE
        if not self.onBoard.isContinuous():
            found = False
            for m in moves:
                if m.containsMove(self.onBoard):
                    found = True
            if not found:
                raise exceptions.TilesNotConnectedException
            
        
        if len(moves) == 0:
            raise exceptions.MoveNotTouchingException
        else:
            return moves
    
    def showBlankLetterDialog(self):
        '''
        Show a dialog box where the user can enter a blank letter
        
        @return: The letter the user entered or ""
        '''
        s = _("Blank Letter")
        dialog = gtk.Dialog(title="%s" % s, parent=None, buttons=(gtk.STOCK_OK, gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.vbox.set_spacing( 10 )
        
        s = _("Enter value for Blank Letter")
        header = gtk.Label()
        header.set_markup("<b><big>%s:</big></b>" % s)
        dialog.vbox.pack_start( header )
        
        entry = gtk.Entry()
        entry.set_width_chars(5)
        entry.connect("key-press-event", self.blankDialogKeyPress_cb, dialog)
        dialog.vbox.pack_start( entry )
        
        dialog.show_all()
        response = dialog.run()
        
        ret = ""
        if response == gtk.RESPONSE_OK:
            data = unicode(entry.get_text(), 'utf-8')
            l = data.upper()
            
            if (not manager.LettersManager().isValidLetter(self.gameOptions[OPTION_RULES], l)):
                self.error(util.ErrorMessage(_("Letter is not a valid scrabble letter")))
            else:
                ret = l
        
        dialog.destroy()
        return ret
        
    ### Callbacks from client ###

    def blankDialogKeyPress_cb(self, widget, event, dialog):
        '''
        Key press event in blank dialog box
        
        @param widget:
        @param event:
        @param dialog
        '''
        if (event.keyval == gtk.keysyms.Return):
            dialog.response( gtk.RESPONSE_OK )
    
    def dragMotion(self, widget, drag_context, x, y, timestamp, bool=False):
        '''
        Callback from the chat window.  If a user drags a tile over the chat window, this prevents
        it from being captured
        
        @param widget:
        @param drag_context:
        @param x:
        @param y:
        @param timestamp:
        @param bool:
        '''
        
        if bool:
            widget.stop_emission("drag-motion")
        
        return False
    
    # Pause the game
    def pauseGame(self):
        '''
        Callback to pause the game
        '''
        
        self.startButton.hide()
        self.saveButton.set_sensitive(True) #Enable save button, game is started
        
        p = gtkutil.Popup( self.currentGameId, _("Game is saved."))
        self.saveButton.set_label(_("Resume Game"))
        self.saveButton.disconnect( self.pauseHandlerId )
        self.pauseHandlerId = self.saveButton.connect("clicked", self.doUnpauseGame)
        self.board.deactivate()
    
    # Unpause the game
    def unpauseGame(self):
        '''
        Callback to unpause the game
        '''
        p = gtkutil.Popup( self.currentGameId,_("Game has been resumed."))
        self.saveButton.set_label(_("Save Game"))
        self.saveButton.disconnect( self.pauseHandlerId )
        self.pauseHandlerId = self.saveButton.connect("clicked", self.doPauseGame)
    
    # Move accepted
    def acceptMove(self):
        '''
        Callback from the server that indicates that the move that was sent has been accepted.
        
        Clear the board and setCurrentTurn = False
        '''
        self.onBoard.clear()
        self.currentTurn = False
        
    
    # Show/Refresh letters in the letter box
    def showLetters(self, letters):
        '''
        Show letters in the letter box
        
        @param letters: List of Letters to show
        '''
                
        # Remove all the widgets
        self.letterBox.foreach(lambda w: w.clear())
        
        for i in range(0, len(letters)):
            letter = letters[i]
            if letter.isBlank():
                letter.setLetter("")
            self.gameLetters[i].copyLetter(letter)
            self.letterBox.show_all()
    
    def refreshUserList(self, users):
        '''
        Show users in the User Window
        
        @param users: List of Players
        '''
        
        self.userList.clear()
        for player in users:
            self.userList.append( (player.name, str(player.score), player.time, str(player.numLetters) ) )
    
    def refreshStats(self, stats):
        '''
        Refresh game stats
        
        C{stats} is a list of tuples (stat_name, value)
        
        @param stats: Stat list
        '''
        self.statList.clear()
        for name,value in stats:
            self.statList.append( (repr(name),value) )
    
    def showDistribution(self, distribution):
        '''
        Show letter distribution
        
        @param distribution: dict(Letter,count)
        '''
        self.distributionList.clear()
        
        d = distribution.items()
        d.sort( lambda (k1,v1), (k2,v2): cmp(k1,k2) )
        
        for letter,count in d:
            self.distributionList.append( (letter, count) )
        
    
    def refreshSpecs(self, specs):
        '''
        Refresh game spectators
        
        C{specs} is a list of Spectators
        
        @param specs: Spectators list
        '''
        self.specList.clear()
        for player in specs:
            self.specList.append( [player.getUsername()] )
        
    
    # Set the current game ID
    def setGame(self, gameId):
        '''
        Set the current game
        
        @param gameId: Game ID
        '''
        self.currentGameId = gameId
        self.currentGame = ScrabbleGame(gameId)
    
    def showError(self, data):
        '''
        Show error dialog
        
        @param data:
        '''
        s = _("Error")
        self.dialog = gtk.MessageDialog(parent=None, type=gtk.MESSAGE_ERROR, message_format="")
        self.dialog.set_title("%s: %s" % (s, self.currentGameId))
        self.dialog.set_markup("<big>%s: %s</big>" % (s, data.getErrorMessage()))
        button = gtk.Button(stock=gtk.STOCK_OK)
        button.connect("clicked", lambda b: self.dialog.destroy())
        self.dialog.action_area.pack_start(button)
        self.dialog.show_all()
        self.dialog.run()
        
    def error(self, data):
        '''
        Game error
        
        @param data: ErrorMessage
        '''
        
        self.showError(data)
        
        if self.isCurrentTurn():
            self.okButton.set_sensitive(True)
        
        o = manager.OptionManager()
        
        if o.get_default_bool_option( OPTION_CLEAR_ON_ERROR, True ):
            self.clearCurrentMoveBackground()
    
    def info(self, log):
        '''
        Game Info Message
        
        C{log} is a list of tuples (type, message)
        
        @param log: Log
        @see: L{pyscrabble.constants}
        '''
        
        for type, message in log:
            message = str(message)
            buf = self.logWindow.get_buffer()
            if type == GAME_LEVEL:
                t = buf.create_tag(foreground=SERVER_MESSAGE)
                self.logWindow.insert_text_with_tags(message, t)
            elif type == SPECTATOR_LEVEL:
                t = buf.create_tag(foreground=SPECTATOR_MESSAGE)
                self.logWindow.insert_text_with_tags(message, t)
            else:
                self.logWindow.insert_text(message)
    
    def infoWindow(self, data):
        '''
        Show Information dialog
        
        @param data: Information text
        '''
        
        s = _("Info")
        self.dialog = gtk.MessageDialog(parent=None, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK, message_format="")
        self.dialog.set_title("%s: %s" % (s, self.currentGameId))
        self.dialog.set_markup("<big>%s: %s</big>" % (s,data))
        self.dialog.connect("response", lambda w,e: self.dialog.destroy())
        self.dialog.show()
        self.dialog.run()
        
    
    def specEnabled_cb(self, button, path, client=False):
        '''
        Callback to allow or disallow Spectators or spectators chatting
        
        @param button: Button that was clicked to activate this callback
        @param client: True if the client initated this action
        '''
        path = int(path)
        self.gameOptionModel[path][1] = not self.gameOptionModel[path][1]
        if client and path == 1:
            self.client.setGameSpectatorChat(self.currentGameId, self.gameOptionModel[path][1])
        if client and path == 0:
            self.client.setGameSpectatorsAllowed(self.currentGameId, self.gameOptionModel[path][1])
    
    def enableSpectatorChat(self, flag):
        '''
        Toggle the Enable Spectator chat button
        
        @param flag: True to enable spectator chat
        '''
        self.gameOptionModel[1][1] = flag
    
    def enableSpectators(self, flag):
        '''
        Toggle the Enable Spectators
        
        @param flag: True to enable spectators
        '''
        self.gameOptionModel[0][1] = flag
    
    def gameBagEmpty(self):
        '''
        Game bag is empty
        
        Hide the trade button and show the letters left column
        '''
        if not self.spectating:
            self.hideTradeButton = True
            self.tradeButton.set_sensitive(False)
        self.userView.get_column(3).set_visible(True)
    
    def askPass(self, button):
        '''
        Confirm that the user wants to pass
        
        @param button: Button that was clicked
        '''
        
        s = _("Are you sure you want to pass")
        dialog = gtk.MessageDialog(parent=None, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="")
        dialog.set_title("%s" % self.currentGameId)
        dialog.set_markup("<big>%s?</big>" % s )
        dialog.show()
        response = dialog.run()
        
        dialog.destroy()
        
        if (response == gtk.RESPONSE_YES):
            self.passMove()
    
    def askLeaveGame_cb(self, button):
        '''
        Ask the user if they want to leave the game
        
        @param button: Widget that activated this callback
        '''
        s = _("Are you sure you want to leave")
        dialog = gtk.MessageDialog(parent=None, type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format="")
        dialog.set_title("%s" % self.currentGameId)
        dialog.set_markup("<big>%s?</big>" % s)
        dialog.show()
        response = dialog.run()
        
        dialog.destroy()
        
        if (response == gtk.RESPONSE_YES):
            self.leaveGame(None)

    def showOptions(self, options):
        '''
        Show options
        
        @param options:
        '''
        
        self.optionList.clear()
        for key,value in options:
            if not isinstance(value,str):
                value = str(value)
            self.optionList.append( [str(key), value] )
            
    
    def notifyFocus(self):
        '''
        This frame now has focus
        
        If we have a recent move pending, start the timer
        '''
        if len(self.recentMoves) > 0:
            reactor.callLater(RECENT_MOVE_TIMEOUT, self.clearRecentMove, self.recentMoves)
        self.recentMoves = []
    
    def clearRecentMove(self, moves):
        '''
        Notify the board to set the recent move tiles to their normal state
        '''
        for move in moves:
            self.board.clearRecentMove(move)
    
    def shuffleLetters_cb(self, widget):
        '''
        Randomly shuffle letters
        '''
        
        letters = self.letterBox.get_children()
        self.letterBox.foreach(lambda w: self.letterBox.remove(w))
        
        #letters = [ l for l in letters if isinstance(l, GameLetter) ]
        random.shuffle(letters)
        for l in letters:
            self.letterBox.pack_start(l, False, False, 0)
        self.letterBox.show_all()
    
    def refreshOptions(self):
        '''
        Refresh options
        '''
        o = manager.OptionManager()
        
        # Refresh board
        self.board.refresh()
        
        # Refresh tips
        if o.get_default_bool_option(OPTION_ENABLE_T_TIPS, True):
            self.tileTips.enable()
        else:
            self.tileTips.disable()
        
        for c in self.letterBox.get_children():
            if isinstance(c, GameLetter):
                c.refresh()
        
    
    def placeLetter(self, letter, x, y):
        '''
        Place a letter on the board
        
        @param letter: Letter
        @param x: X
        @param y: Y
        '''
        
        tmp = self.letterBox.get_children()
        
        l = None
        for _letter in tmp:
            if isinstance(_letter, GameLetter):
                if _letter.getLetter().getLetter() == letter:
                    l = _letter
        
        if l is None:
            for _letter in tmp:
                if isinstance(_letter, GameLetter):
                    if _letter.isBlank() and _letter.getLetter().getLetter() == "":
                        l = _letter
                        l.setLetter( letter )
                        l.setIsBlank( True )
                        break
                        
        if l is None:
            gtk.gdk.beep()
            return False
            
        tile = self.board.get(x,y)
        _l = l.getLetter()
        tile.setLetter(l, _l.getLetter(), _l.getScore(), _l.isBlank(), showBlank=False)
        return True
    
    def selectAllLetters(self):
        '''
        Select all letters
        '''
        for item in self.letterBox.get_children():
            if isinstance(item, GameLetter):
                item.set_active( not item.get_active() )
    
    def optionViewWidthChanged_cb(self, col, val, pos):
        '''
        
        @param view:
        @param val:
        @param pos:
        '''
        c = self.gameOptionView.get_column(pos)
        c.set_min_width(col.get_width())
    
    def isCurrentTurn(self):
        '''
        Check if its the users turn
        
        @return: True if the user has control of the board
        '''
        return self.currentGame.getCurrentPlayer().getUsername() == self.player.getUsername()
    
    def getGameOption(self, opt):
        '''
        Get game option
        
        @param opt: Option name
        @return: Option value
        '''
        return self.gameOptions[opt]
        
