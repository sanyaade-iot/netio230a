#!/usr/bin/env python
# -*- encoding: UTF8 -*-

# author: Philipp Klaus, philipp.l.klaus AT web.de


#   This file is part of netio230a.
#
#   netio230a is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   netio230a is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with netio230a.  If not, see <http://www.gnu.org/licenses/>.


# documentation on PyGTK:
# http://library.gnome.org/devel/pygtk/stable/
# http://library.gnome.org/devel/pygobject/stable/

import sys
import os # for os.path.abspath() and os.path.dirname()
import gtk
## for debugging (set debug mark with pdb.set_trace() )
import pdb
import netio230a


class DeviceController:
    def __init__(self,controller,connection_details):
        self.controller = controller
    
        self.__host = connection_details['host']
        self.__tcp_port = connection_details['tcp_port']
        self.__username = connection_details['username']
        self.__pw = connection_details['password']
        try:
            self.netio = netio230a.netio230a(self.__host, self.__username, self.__pw, True, self.__tcp_port)
        except StandardError, error:
            print str(error)
        
        fullpath = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.builder = gtk.Builder()
        self.builder.add_from_file(fullpath + "/resources/netio230aGUI.glade") 
        
        self.window = self.builder.get_object("mainWindow")
        self.about_dialog = self.builder.get_object( "aboutDialog" )
        
        self.builder.connect_signals(self)
        
        self.__updatePowerSocketStatus()
        self.window.show()
    
    def cb_disconnect(self, button, *args):
        self.controller.setNextStep("runDeviceSelector")
        gtk.main_quit()
        self.window.hide()
        return False
    
    def gtk_main_quit( self, window ):
        gtk.main_quit()
    
    def on_window_destroy(self, widget, data=None):
        gtk.main_quit()
    
    def cb_about(self, button):
        self.about_dialog.run()
        self.about_dialog.hide()
        
    def cb_updateDisplay(self, notebook, page, page_num):
        if page_num == 0:
            self.__updatePowerSocketStatus()
        elif page_num == 1:
            self.__updateSystemSetup()
        elif page_num == 2:
            try:
                power_sockets = self.netio.getAllPowerSockets()
            except StandardError:
                print("could not connect")
                return
            
            netio = None
            for i in range(4):
                ## shorter form with builder.get_object(). cf. <http://stackoverflow.com/questions/2072976/access-to-widget-in-gtk>
                self.builder.get_object("socket"+str(i+1)).set_active(power_sockets[i].getPowerOn())
        else:
            return
    
    def cb_refresh(self, button):
        self.__updatePowerSocketStatus()

    def __updatePowerSocketStatus(self):
        try:
            power_sockets = self.netio.getAllPowerSockets()
        except StandardError, error:
            print(str(error))
            return
        self.netio.disconnect()
        tb = gtk.TextBuffer()
        tb.set_text("power status:\nsocket 1: %s\nsocket 2: %s\nsocket 3: %s\nsocket 4: %s" % (power_sockets[0].getPowerOn(),power_sockets[1].getPowerOn(),power_sockets[2].getPowerOn(),power_sockets[3].getPowerOn()))
        self.builder.get_object("status_output").set_buffer( tb )
    
    
    
    def __updateSystemSetup(self):
        try:
            deviceAlias = self.netio.getDeviceAlias()
            version = self.netio.getFirmwareVersion()
            systemTime = self.netio.getSystemTime().isoformat(" ")
            timezoneOffset = self.netio.getSystemTimezone()
            sntpSettings = self.netio.getSntpSettings()
        except StandardError, error:
            print(str(error))
            return
        self.netio.disconnect()
        self.builder.get_object("device_name").set_text( deviceAlias )
        self.builder.get_object("firmware_version").set_text( version )
        self.builder.get_object("system_time").set_text( systemTime )
        self.builder.get_object("timezone_offset").set_text( str(timezoneOffset) + " hours" )
        self.builder.get_object("sntp_settings").set_text( sntpSettings )
    
        
    def cb_switch1On(self, togglebutton):
        self.__setPowerSocket(1,togglebutton.get_active())
    
    def cb_switch2On(self, togglebutton):
        self.__setPowerSocket(2,togglebutton.get_active())
    
    def cb_switch3On(self, togglebutton):
        self.__setPowerSocket(3,togglebutton.get_active())
    
    def cb_switch4On(self, togglebutton):
        self.__setPowerSocket(4,togglebutton.get_active())
    
    def __setPowerSocket(self,socket_nr,socket_power=True):
        try:
            self.netio.setPowerSocketPower(socket_nr,socket_power)
        except StandardError, error:
            print(str(error))
        self.netio.disconnect()

class ConnectionDetailDialog:
    def __init__(self,host='',username='admin',password='',tcp_port=1234):
        fullpath = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.builder = gtk.Builder()
        self.builder.add_from_file(fullpath + "/resources/netio230aGUI_dialog.glade")
        self.dialog = self.builder.get_object("ConnectionDetailDialog")
        self.builder.get_object("host_text").set_text(host)
        self.builder.get_object("port_text").set_text(str(tcp_port))
        self.builder.get_object("username_text").set_text(username)
        self.builder.get_object("password_text").set_text(password)
    
    def run(self):
        self.builder.connect_signals(self)
        return self.dialog.run()
        
    
    def updateData(self):
        self.__host = self.builder.get_object("host_text").get_text()
        self.__username = self.builder.get_object("username_text").get_text()
        self.__pw = self.builder.get_object("password_text").get_text()
        try:
            self.__tcp_port = int(self.builder.get_object("port_text").get_text())
        except:
            self.__tcp_port = 0
            self.builder.get_object("port_text").set_text("0")
    
    def response_handler(self, dialog, response_id):
        self.updateData()
    
    def getData(self):
        data = dict()
        data['host'] = self.__host
        data['username'] = self.__username
        data['password'] = self.__pw
        data['tcp_port'] = self.__tcp_port
        return data
        

class DeviceSelector:
    # close the window and quit
    def delete_event(self, widget, event, data=None):
        gtk.main_quit()

    def __init__(self, controller):
        self.controller = controller
        # Create a new window
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Basic TreeView Example")
        self.window.set_size_request(300, 200)
        self.window.connect("delete_event", self.delete_event)

        # create a TreeStore with two string columns to use as the model
        self.treestore = gtk.TreeStore(str,str)

        devices = netio230a.get_all_detected_devices()
        piter = self.treestore.append(None,['auto-detected devices',''])
        for device in devices:
            self.treestore.append(piter,[device[0],str(device[1][0])+'.'+str(device[1][1])+'.'+str(device[1][2])+'.'+str(device[1][3])])
        
        # more on TreeViews: <http://www.thesatya.com/blog/2007/10/pygtk_treeview.html>
        # and <http://www.pygtk.org/pygtk2tutorial/ch-TreeViewWidget.html#sec-TreeViewOverview>
        # create the TreeView using treestore
        self.treeview = gtk.TreeView(self.treestore)
        # create the TreeViewColumn to display the data
        self.tvcolumn = gtk.TreeViewColumn('Device Name')
        self.tvcolumn1 = gtk.TreeViewColumn('IP Address')
        # add tvcolumn to treeview
        self.treeview.append_column(self.tvcolumn)
        self.treeview.append_column(self.tvcolumn1)
        # create a CellRendererText to render the data
        self.cell = gtk.CellRendererText()
        # add the cell to the tvcolumn and allow it to expand
        self.tvcolumn.pack_start(self.cell, True)
        self.tvcolumn1.pack_start(self.cell, True)
        # set the cell "text" attribute to column 0 - retrieve text
        # from that column in treestore
        self.tvcolumn.add_attribute(self.cell, 'text', 0)
        self.tvcolumn1.add_attribute(self.cell, 'text', 1)
        # make it searchable
        self.treeview.set_search_column(0)
        # Allow sorting on the column
        self.tvcolumn.set_sort_column_id(0)
        self.tvcolumn1.set_sort_column_id(1)
        # Allow drag and drop reordering of rows
        self.treeview.set_reorderable(True)
        self.treeview.expand_all()

        spacing, homogeneous, expand, fill, padding = 2, True, False, False, 2
        # Create a new hbox with the appropriate homogeneous
        # and spacing settings
        box = gtk.HBox(homogeneous, spacing)
        
        # create the buttons
        button = gtk.Button("other device")
        box.pack_start(button, expand, fill, padding)
        button = gtk.Button("connect")
        box.pack_start(button, expand, fill, padding)
        button.connect("clicked",self.connect_clicked, self.treeview)
        
        spacing, homogenious, expand, fill, padding = 2, True, False, False, 2
        superbox = gtk.VBox(homogeneous, spacing)
        superbox.pack_start(self.treeview, True, True, 1)
        superbox.pack_start(box, False, False, 2)
        
        self.superbox = superbox
        
        self.window.add(self.superbox)
        self.window.show_all()
        
    def connect_clicked(self, button, *args):
        for arg in args:
            if type(arg)==gtk.TreeView:
                (model, treeiter) = arg.get_selection().get_selected()
                host = model.get_value(treeiter,1)
                
                #dlg = gtk.Dialog(title='Ein Dialog',
                #    parent=self.window,
                #    buttons=(gtk.STOCK_CANCEL,
                #             gtk.RESPONSE_REJECT,
                #             gtk.STOCK_OK,
                #             gtk.RESPONSE_OK))
                #result = dlg.run()
                #if result == gtk.RESPONSE_OK:
                #    print 'Mach mal!'
                #else:
                #    print 'Lieber nicht.'
                #dlg.destroy()
                dl = ConnectionDetailDialog(host)
                result = dl.run()
                while result == 1:
                    data = dl.getData()
                    try:
                        netio = netio230a.netio230a(data['host'], data['username'], data['password'], True, data['tcp_port'])
                        netio = None
                        break
                    except StandardError, error:
                        print str(error)
                        dl.dialog.hide()
                        del dl
                        dl = ConnectionDetailDialog(data['host'], data['username'], data['password'], data['tcp_port'])
                        result = dl.run()
                        print "schon wieder",result
                
                dl.dialog.hide()
                del dl
                if result != 1:
                    return
                
                self.controller.setNextStep("runDeviceController", host = data['host'], tcp_port = data['tcp_port'], username=data['username'], password = data['password'])
                #self.window.hide()
                self.window.destroy()
                gtk.main_quit()
                return False
    
    def show_connection_details_dialog(self,host):
          dialog = gtk.Dialog(title="Please provice details for the connection", parent=self.window, flags=0, buttons=None)
          #where title is the text to be used in the titlebar, parent is the main application window and flags set various modes of operation for the dialog:
          #DIALOG_MODAL - make the dialog modal
          #DIALOG_DESTROY_WITH_PARENT - destroy dialog when its parent is destroyed
          #DIALOG_NO_SEPARATOR - omit the separator between the vbox and the action_area
          #The buttons argument is a tuple of button text and response pairs. All arguments have defaults and can be specified using keywords.

          #This will create the dialog box, and it is now up to you to use it. You could pack a button in the action_area:
          button = gtk.Button('test')
          dialog.action_area.pack_start(button, True, True, 0)
          button.show()

          #And you could add to the vbox area by packing, for instance, a label in it, try something like this:
          label = gtk.Label("Dialogs are groovy")
          dialog.vbox.pack_start(label, True, True, 0)
          label.show()
          return dialog.show()



class Controller(object):
    def run(self):
        icon = gtk.StatusIcon()
        icon.set_from_file('./resources/netio230a_icon.png')
        self.nextStep = "runDeviceSelector"
        while self.nextStep != "":
            if self.nextStep == "runDeviceSelector":
                self.nextStep = ""
                self.runDeviceSelector()
            elif self.nextStep == "runDeviceController":
                self.nextStep = ""
                self.runDeviceController(self.nextStepKWArgs)
    
    def setNextStep(self,what, **kwargs):
        self.nextStep = what
        self.nextStepKWArgs = kwargs
    
    def runDeviceSelector(self):
        tvexample = DeviceSelector(self)
        gtk.main()
    
    def runDeviceController(self, connection_details):
        tvexample = DeviceController(self, connection_details)
        gtk.main()


def main():
    controller = Controller()
    controller.run()

if __name__ == "__main__":
    main()

