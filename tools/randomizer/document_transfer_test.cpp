#include "document_transfer.h"
#include <cassert>
#include <iostream>
using namespace RetunedRandomizer;
int main() {
    RetunedFrontend::RandomizerMenuState menu;
    menu.Refresh=[]{};menu.Create=[](unsigned,const std::string&){};menu.Start=[](unsigned){};
    bool startup=true,accept=true;unsigned imported=0,opened=0;
    std::string received;
    menu.Import=[&](unsigned slot,const std::string& bytes){assert(slot==0);++imported;received=bytes;};
    menu.Export=[](unsigned){return std::string("export bytes");};
    std::optional<DocumentResult> result;
    DocumentTransfer transfer(menu,[&]{return startup;},
        [&](unsigned,bool,const std::string&){++opened;return accept;},
        [&]{auto value=std::move(result);result.reset();return value;});
    menu.ChooseImport(0);assert(menu.TransferBusy && !menu.CanCreate(0,true));
    menu.ChooseImport(1);assert(opened==1);
    result=DocumentResult{0,false,false,"exact UTF-8 bytes: \xf0\x9f\x8e\xb2",{}};
    transfer.Poll();assert(imported==1 && received=="exact UTF-8 bytes: \xf0\x9f\x8e\xb2" && !menu.TransferBusy);
    result=DocumentResult{0,false,false,"duplicate",{}};transfer.Poll();assert(imported==1);
    menu.ChooseImport(0);result=DocumentResult{0,false,true,{},{}};transfer.Poll();assert(imported==1 && !menu.TransferBusy);
    menu.ChooseImport(0);result=DocumentResult{1,false,false,"wrong slot",{}};transfer.Poll();assert(imported==1);
    menu.ChooseImport(0);startup=false;result=DocumentResult{0,false,false,"late result",{}};transfer.Poll();assert(imported==1);
    startup=true;menu.ChooseImport(0);menu.Slots[0].Status=RetunedFrontend::RandomizerSlotStatus::Ready;
    result=DocumentResult{0,false,false,"occupied slot",{}};transfer.Poll();assert(imported==1);
    menu.ChooseExport(0);result=DocumentResult{0,true,false,{},{}};transfer.Poll();assert(menu.TransferStatus=="Run exported.");
    menu.Slots[0].Status=RetunedFrontend::RandomizerSlotStatus::Empty;
    menu.ChooseImport(0);result=DocumentResult{0,false,false,std::string(DocumentTransfer::Limit+1,'x'),{}};
    transfer.Poll();assert(imported==1 && !menu.TransferBusy);
    menu.ChooseImport(0);result=DocumentResult{0,false,false,{},"provider error"};transfer.Poll();assert(menu.TransferStatus=="provider error");
    accept=false;menu.ChooseImport(0);assert(!menu.TransferBusy && !menu.TransferStatus.empty());
    std::cout<<"Document transfer checks passed\n";
}
