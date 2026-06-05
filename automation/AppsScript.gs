// ================================================================
// PROPERTY PORTFOLIO DASHBOARD — SETUP SCRIPT v2
//
// Run these functions ONE AT A TIME in this order:
//   1. step1_CreateTabs
//   2. step2_BuildSettings
//   3. step3_BuildHistory
//   4. step4_BuildPendingReview
//   5. step5_BuildMaintenanceLog
//   6. step6_BuildLoans
//   7. step7_BuildTaxSummary
//   8. step8_BuildDistributions
//   9. step9_BuildDashboard
// ================================================================

var LLCS = [
  'Yale Townhomes, LLC',
  '5070 Donald, LLC',
  'Divando LLC',
  'Dorado LLC'
];

var C = {
  headerBg:   '#1a1a2e',
  accentBg:   '#0f3460',
  lightGreen: '#C8E6C9',
  darkGreen:  '#1B5E20',
  lightRed:   '#FFCDD2',
  darkRed:    '#B71C1C',
  lightYellow:'#FFF9C4',
  lightBlue:  '#BBDEFB',
  white:      '#ffffff',
  offWhite:   '#f8f9fa',
  lightGray:  '#f1f3f4',
  midGray:    '#e0e0e0',
  darkGray:   '#757575',
  textDark:   '#212121'
};

// ── STEP 1: Create all 8 tabs ────────────────────────────────────
function step1_CreateTabs() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tabs = ['Dashboard','History','Pending Review','Settings',
              'Maintenance Log','Loans','Tax Summary','Distributions'];

  tabs.forEach(function(name) {
    if (!ss.getSheetByName(name)) ss.insertSheet(name);
  });

  ss.getSheets().forEach(function(sh) {
    if (tabs.indexOf(sh.getName()) === -1) {
      try { ss.deleteSheet(sh); } catch(e) {}
    }
  });

  tabs.forEach(function(name, i) {
    ss.setActiveSheet(ss.getSheetByName(name));
    ss.moveActiveSheet(i + 1);
  });

  var colors = {'Dashboard':'#f44336','History':'#4CAF50',
    'Pending Review':'#FFC107','Settings':'#0f3460',
    'Maintenance Log':'#FF9800','Loans':'#9C27B0',
    'Tax Summary':'#607D8B','Distributions':'#00BCD4'};
  tabs.forEach(function(name) {
    ss.getSheetByName(name).setTabColor(colors[name]);
  });

  SpreadsheetApp.getUi().alert('✅ Step 1 done — 8 tabs created.\n\nNow run step2_BuildSettings.');
}

// ── STEP 2: Settings ─────────────────────────────────────────────
function step2_BuildSettings() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Settings');
  sh.clear();

  sh.getRange('A1').setValue('⚙️  SETTINGS').setFontSize(20).setFontWeight('bold');

  sh.getRange('A3').setValue('AUTOMATION MODE').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange('A4').setValue('Require Approval Before Saving');
  sh.getRange('B4').setValue('YES').setFontWeight('bold')
    .setBackground(C.lightYellow).setHorizontalAlignment('center').setFontSize(12);
  sh.getRange('C4').setValue('← Change to NO once you trust the system')
    .setFontColor(C.darkGray).setFontStyle('italic');
  sh.getRange('B4').setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(['YES','NO'],true).build());

  sh.getRange('A6').setValue('FIXED COSTS PER LLC').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange('A7').setValue('💡 Enter annual amounts for Tax and Insurance — divided by 12 automatically.')
    .setFontColor(C.darkGray).setFontStyle('italic');

  var hdrs = ['LLC Name','Monthly Mortgage ($)','Annual Property Tax ($)','Annual Insurance ($)','Est. Property Value ($)'];
  sh.getRange(8,1,1,5).setValues([hdrs])
    .setBackground(C.headerBg).setFontColor(C.white).setFontWeight('bold').setHorizontalAlignment('center');

  LLCS.forEach(function(llc, i) {
    var row = 9 + i;
    var bg = i % 2 === 0 ? C.offWhite : C.lightGray;
    sh.getRange(row,1).setValue(llc).setBackground(bg).setFontWeight('bold');
    sh.getRange(row,2,1,4).setBackground(bg).setNumberFormat('$#,##0.00');
  });

  var pr = 9 + LLCS.length + 2;
  sh.getRange(pr,1).setValue('PARTNER ACCESS').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange(pr+1,1).setValue("Partner's Email Address");
  sh.getRange(pr+1,2).setBackground(C.lightBlue);

  sh.getRange(pr+3,1).setValue('NOTIFICATIONS').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange(pr+4,1).setValue('Your Email (for automation alerts)');
  sh.getRange(pr+4,2).setBackground(C.lightBlue);

  [220,190,200,190,200].forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(8);

  SpreadsheetApp.getUi().alert('✅ Step 2 done — Settings tab ready.\n\nNow run step3_BuildHistory.');
}

// ── STEP 3: History ──────────────────────────────────────────────
function step3_BuildHistory() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('History');
  sh.clear();

  var hdrs = ['Date Range','Period Start','LLC',
    'Owner Disbursements ($)','Management Fees ($)',
    'Mortgage/mo ($)','Tax/12 ($)','Insurance/12 ($)','Maintenance ($)',
    'Net Cashflow ($)','Source','Logged At'];
  sh.getRange(1,1,1,12).setValues([hdrs])
    .setBackground(C.headerBg).setFontColor(C.white)
    .setFontWeight('bold').setHorizontalAlignment('center').setWrap(true);
  sh.setRowHeight(1,40);

  sh.getRange('B2:B500').setNumberFormat('MM/dd/yyyy');
  sh.getRange('D2:J500').setNumberFormat('$#,##0.00');
  sh.getRange('L2:L500').setNumberFormat('MM/dd/yyyy HH:mm');

  [180,110,200,170,160,130,110,130,120,130,160,160]
    .forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(1);

  SpreadsheetApp.getUi().alert('✅ Step 3 done — History tab ready.\n\nNow run step4_BuildPendingReview.');
}

// ── STEP 4: Pending Review ───────────────────────────────────────
function step4_BuildPendingReview() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Pending Review');
  sh.clear();

  sh.getRange('A1:L1').merge()
    .setValue('⏳  PENDING REVIEW — Check numbers, then use  📊 Portfolio Tools → Approve & Save')
    .setBackground('#FFC107').setFontColor(C.textDark)
    .setFontWeight('bold').setHorizontalAlignment('center').setFontSize(12);
  sh.setRowHeight(1,36);

  var hdrs = ['Date Range','Period Start','LLC',
    'Owner Disbursements ($)','Management Fees ($)',
    'Mortgage/mo ($)','Tax/12 ($)','Insurance/12 ($)','Maintenance ($)',
    'Net Cashflow ($)','Source','Logged At'];
  sh.getRange(2,1,1,12).setValues([hdrs])
    .setBackground(C.accentBg).setFontColor(C.white)
    .setFontWeight('bold').setHorizontalAlignment('center').setWrap(true);
  sh.setRowHeight(2,40);

  sh.getRange('B3:B500').setNumberFormat('MM/dd/yyyy');
  sh.getRange('D3:J500').setNumberFormat('$#,##0.00');
  sh.getRange('L3:L500').setNumberFormat('MM/dd/yyyy HH:mm');

  [180,110,200,170,160,130,110,130,120,130,160,160]
    .forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(2);

  SpreadsheetApp.getUi().alert('✅ Step 4 done — Pending Review tab ready.\n\nNow run step5_BuildMaintenanceLog.');
}

// ── STEP 5: Maintenance Log ──────────────────────────────────────
function step5_BuildMaintenanceLog() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Maintenance Log');
  sh.clear();

  sh.getRange('A1').setValue('🔧  MAINTENANCE LOG').setFontSize(18).setFontWeight('bold');
  sh.getRange('A2').setValue('Enter invoices anytime — independently of the monthly automation.')
    .setFontColor(C.darkGray).setFontStyle('italic');

  sh.getRange(4,1,1,5).setValues([['Date','LLC','Description','Amount ($)','Entered By']])
    .setBackground(C.headerBg).setFontColor(C.white).setFontWeight('bold').setHorizontalAlignment('center');

  sh.getRange('A5:A200').setNumberFormat('MM/dd/yyyy');
  sh.getRange('B5:B200').setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(LLCS,true).build());
  sh.getRange('D5:D200').setNumberFormat('$#,##0.00');

  [110,200,320,130,160].forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(4);

  SpreadsheetApp.getUi().alert('✅ Step 5 done — Maintenance Log ready.\n\nNow run step6_BuildLoans.');
}

// ── STEP 6: Loans ────────────────────────────────────────────────
function step6_BuildLoans() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Loans');
  sh.clear();

  sh.getRange('A1').setValue('🏦  LOANS').setFontSize(18).setFontWeight('bold');
  sh.getRange('A2:L2').merge()
    .setValue('Enter each loan once. Calculated Balance updates automatically. Use Override only if you refinanced or made extra payments.')
    .setFontColor(C.darkGray).setFontStyle('italic').setWrap(true);

  var hdrs = ['LLC','Lender Name','Loan Number','Lender Contact',
    'Original Balance ($)','Interest Rate (%)','Term (months)',
    'Start Date','Monthly Payment ($)','Maturity Date',
    'Balance Override ($)','Calculated Balance ($)'];
  sh.getRange(4,1,1,12).setValues([hdrs])
    .setBackground(C.headerBg).setFontColor(C.white)
    .setFontWeight('bold').setHorizontalAlignment('center').setWrap(true);
  sh.setRowHeight(4,45);

  var loans = [
    ['5070 Donald, LLC',    'SBA',      '','','','','','','','','',''],
    ['5070 Donald, LLC',    'CBRE',     '','','','','','','','','',''],
    ['Yale Townhomes, LLC', 'Lument',   '','','','','','','','','',''],
    ['Divando LLC',         'SBA',      '','','','','','','','','',''],
    ['Dorado LLC',          'PAID OFF', 'N/A','N/A',0,0,0,'',0,'N/A',0,'']
  ];
  sh.getRange(5,1,loans.length,12).setValues(loans);

  for (var i = 0; i < 5; i++) {
    var row = 5 + i;
    sh.getRange(row,12).setFormula(
      '=IF(K'+row+'<>"",K'+row+',IF(H'+row+'="","Enter start date",IF(F'+row+'=0,0,'+
      'MAX(0,PV(F'+row+'/100/12,G'+row+'-IFERROR(DATEDIF(H'+row+',TODAY(),"M"),0),-I'+row+')))))'
    );
  }

  sh.getRange('E5:E20').setNumberFormat('$#,##0.00');
  sh.getRange('F5:F20').setNumberFormat('0.00');
  sh.getRange('H5:H20').setNumberFormat('MM/dd/yyyy');
  sh.getRange('I5:I20').setNumberFormat('$#,##0.00');
  sh.getRange('K5:K20').setNumberFormat('$#,##0.00');
  sh.getRange('L5:L20').setNumberFormat('$#,##0.00').setBackground(C.lightGreen).setFontWeight('bold');

  sh.getRange('A5:A20').setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(LLCS,true).build());

  [200,140,130,200,160,120,120,110,160,120,160,190]
    .forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(4);

  SpreadsheetApp.getUi().alert('✅ Step 6 done — Loans tab ready.\n\nNow run step7_BuildTaxSummary.');
}

// ── STEP 7: Tax Summary ──────────────────────────────────────────
function step7_BuildTaxSummary() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Tax Summary');
  sh.clear();

  sh.getRange('A1').setValue('📊  ANNUAL TAX SUMMARY').setFontSize(18).setFontWeight('bold');
  sh.getRange('A2:I2').merge()
    .setValue('Auto-built from the History tab. Share with your accountant at year end — no extra work needed.')
    .setFontColor(C.darkGray).setFontStyle('italic').setWrap(true);

  var hdrs = ['Year','LLC','Total Disbursements','Total Mgmt Fees','Total Maintenance',
    'Total Mortgage Paid','Total Tax Paid','Total Insurance Paid','Net Cashflow'];
  sh.getRange(4,1,1,9).setValues([hdrs])
    .setBackground(C.headerBg).setFontColor(C.white)
    .setFontWeight('bold').setHorizontalAlignment('center').setWrap(true);
  sh.setRowHeight(4,40);

  var currentYear = new Date().getFullYear();
  var years = [currentYear, currentYear-1, currentYear-2];
  var row = 5;

  years.forEach(function(yr) {
    var yrStart = row;
    LLCS.forEach(function(llc, i) {
      sh.getRange(row,1).setValue(yr);
      sh.getRange(row,2).setValue(llc);

      // History columns: B=PeriodStart, C=LLC, D=Disb, E=Mgmt, F=Mort, G=Tax/12, H=Ins/12, I=Maint, J=Net
      var cols = {3:'D',4:'E',5:'I',6:'F',7:'G',8:'H',9:'J'};
      Object.keys(cols).forEach(function(c) {
        var hc = cols[c];
        sh.getRange(row,parseInt(c)).setFormula(
          '=IFERROR(SUMPRODUCT((YEAR(History!$B$2:$B$500)='+yr+')*'+
          '(History!$C$2:$C$500="'+llc+'")*History!$'+hc+'$2:$'+hc+'$500),0)'
        );
      });
      sh.getRange(row,1,1,9).setBackground(i%2===0 ? C.offWhite : C.lightGray);
      row++;
    });

    // Total row
    sh.getRange(row,1).setValue(yr+' TOTAL').setFontWeight('bold');
    sh.getRange(row,2).setValue('ALL LLCs').setFontWeight('bold');
    for (var c=3; c<=9; c++) {
      var l = ['','A','B','C','D','E','F','G','H','I'][c];
      sh.getRange(row,c).setFormula('=SUM('+l+yrStart+':'+l+(row-1)+')').setFontWeight('bold');
    }
    sh.getRange(row,1,1,9).setBackground(C.lightBlue).setFontWeight('bold');
    row += 2;
  });

  sh.getRange('C5:I'+row).setNumberFormat('$#,##0.00');
  [80,200,180,160,160,170,150,170,140].forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(4);

  SpreadsheetApp.getUi().alert('✅ Step 7 done — Tax Summary ready.\n\nNow run step8_BuildDistributions.');
}

// ── STEP 8: Distributions ────────────────────────────────────────
function step8_BuildDistributions() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Distributions');
  sh.clear();

  sh.getRange('A1').setValue('💸  DISTRIBUTIONS').setFontSize(18).setFontWeight('bold');
  sh.getRange('A2:F2').merge()
    .setValue('Enter monthly distributions manually. You or your partner can fill this in anytime.')
    .setFontColor(C.darkGray).setFontStyle('italic');

  sh.getRange(4,1,1,6).setValues([['Month','LLC','Your Amount ($)','Partner Amount ($)','Date Sent','Notes']])
    .setBackground(C.headerBg).setFontColor(C.white).setFontWeight('bold').setHorizontalAlignment('center');

  sh.getRange('A5:A200').setNumberFormat('MMM yyyy');
  sh.getRange('B5:B200').setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(LLCS,true).build());
  sh.getRange('C5:D200').setNumberFormat('$#,##0.00');
  sh.getRange('E5:E200').setNumberFormat('MM/dd/yyyy');

  [100,200,160,170,120,260].forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(4);

  SpreadsheetApp.getUi().alert('✅ Step 8 done — Distributions tab ready.\n\nNow run step9_BuildDashboard.');
}

// ── STEP 9: Dashboard ────────────────────────────────────────────
function step9_BuildDashboard() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Dashboard');
  sh.clear();
  sh.clearConditionalFormatRules();

  // Title
  sh.getRange('A1:I1').merge()
    .setValue('🏠  PROPERTY PORTFOLIO DASHBOARD')
    .setBackground(C.headerBg).setFontColor(C.white)
    .setFontSize(22).setFontWeight('bold').setHorizontalAlignment('center').setVerticalAlignment('middle');
  sh.setRowHeight(1,55);

  // Last update bar
  sh.getRange('A2').setValue('Last Updated:').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange('B2').setValue('Not yet run').setFontColor(C.darkGray).setFontStyle('italic');
  sh.getRange('D2').setValue('Source:').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange('E2').setValue('—').setFontColor(C.darkGray).setFontStyle('italic');
  sh.getRange('G2').setValue('Distributions this month:').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange('H2').setValue('—').setFontColor(C.darkGray).setFontStyle('italic');
  sh.getRange('A2:I2').setBackground(C.offWhite);
  sh.setRowHeight(2,28);

  // Section label
  sh.getRange('A4').setValue("THIS MONTH'S CASHFLOW SUMMARY")
    .setFontWeight('bold').setFontColor(C.darkGray);

  // Column headers
  var hdrs = ['LLC','Disbursements','Mgmt Fees','Mortgage','Tax /12','Insurance /12','Maintenance','Net Cashflow','Est. Equity'];
  sh.getRange(5,1,1,9).setValues([hdrs])
    .setBackground(C.accentBg).setFontColor(C.white).setFontWeight('bold').setHorizontalAlignment('center');

  // One row per LLC
  LLCS.forEach(function(llc, i) {
    var row = 6 + i;
    var bg = i%2===0 ? C.offWhite : C.lightGray;
    var q = '"'+llc+'"';
    sh.getRange(row,1).setValue(llc).setFontWeight('bold').setBackground(bg);

    function histLookup(col) {
      return '=IFERROR(INDEX(History!$'+col+':$'+col+
        ',MATCH(1,(History!$C:$C='+q+')*(History!$B:$B=MAXIFS(History!$B:$B,History!$C:$C,'+q+')),0)),"—")';
    }

    ['D','E','F','G','H','I','J'].forEach(function(col, ci) {
      sh.getRange(row, ci+2).setFormula(histLookup(col)).setNumberFormat('$#,##0.00').setBackground(bg);
    });

    // Equity
    sh.getRange(row,9)
      .setFormula('=IFERROR(SUMIF(Settings!$A$9:$A$12,'+q+',Settings!$E$9:$E$12)-SUMIF(Loans!$A:$A,'+q+',Loans!$L:$L),"—")')
      .setNumberFormat('$#,##0.00').setBackground(bg);
  });

  // Total row
  var totRow = 6 + LLCS.length;
  sh.getRange(totRow,1).setValue('TOTAL ALL LLCs').setFontWeight('bold');
  ['B','C','D','E','F','G','H','I'].forEach(function(col,i) {
    sh.getRange(totRow,i+2)
      .setFormula('=IFERROR(SUMIF('+col+'6:'+col+(totRow-1)+',"<>—"),"—")')
      .setNumberFormat('$#,##0.00').setFontWeight('bold');
  });
  sh.getRange(totRow,1,1,9).setBackground(C.lightBlue).setFontWeight('bold');

  // Conditional formatting on Net Cashflow (col H = col 8)
  var cfRange = sh.getRange(6,8,LLCS.length+1,1);
  sh.setConditionalFormatRules([
    SpreadsheetApp.newConditionalFormatRule()
      .whenNumberGreaterThan(0).setBackground(C.lightGreen).setFontColor(C.darkGreen)
      .setRanges([cfRange]).build(),
    SpreadsheetApp.newConditionalFormatRule()
      .whenNumberLessThan(0).setBackground(C.lightRed).setFontColor(C.darkRed)
      .setRanges([cfRange]).build()
  ]);

  // Loan balances section
  var lSec = totRow + 2;
  sh.getRange(lSec,1).setValue('LOAN BALANCES').setFontWeight('bold').setFontColor(C.darkGray);
  sh.getRange(lSec+1,1,1,5).setValues([['LLC','Lender','Remaining Balance','Maturity Date','Monthly Payment']])
    .setBackground(C.accentBg).setFontColor(C.white).setFontWeight('bold').setHorizontalAlignment('center');

  for (var li=0; li<5; li++) {
    var lr = lSec+2+li;
    var lRow = 5+li;
    sh.getRange(lr,1).setFormula('=IFERROR(Loans!A'+lRow+',"")');
    sh.getRange(lr,2).setFormula('=IFERROR(Loans!B'+lRow+',"")');
    sh.getRange(lr,3).setFormula('=IFERROR(Loans!L'+lRow+',"")').setNumberFormat('$#,##0.00');
    sh.getRange(lr,4).setFormula('=IFERROR(Loans!J'+lRow+',"")').setNumberFormat('MM/dd/yyyy');
    sh.getRange(lr,5).setFormula('=IFERROR(Loans!I'+lRow+',"")').setNumberFormat('$#,##0.00');
    sh.getRange(lr,1,1,5).setBackground(li%2===0 ? C.offWhite : C.lightGray);
  }

  [200,140,140,120,110,130,120,140,150].forEach(function(w,i){ sh.setColumnWidth(i+1,w); });
  sh.setFrozenRows(2);
  ss.setActiveSheet(sh);

  SpreadsheetApp.getUi().alert('✅ Step 9 done — Dashboard is ready!\n\nAll 8 tabs are complete. Go back to your spreadsheet and check it out!');
}

// ── APPROVE & SAVE ───────────────────────────────────────────────
function approveAndSave() {
  var ss      = SpreadsheetApp.getActiveSpreadsheet();
  var pending = ss.getSheetByName('Pending Review');
  var history = ss.getSheetByName('History');
  var ui      = SpreadsheetApp.getUi();

  var lastRow = pending.getLastRow();
  if (lastRow < 3) { ui.alert('Nothing to approve — Pending Review is empty.'); return; }

  var data      = pending.getRange(3,1,lastRow-2,12).getValues();
  var validRows = data.filter(function(r){ return r[0]!=='' && r[2]!==''; });
  if (!validRows.length) { ui.alert('No valid rows found.'); return; }

  var ok = ui.alert('Approve & Save','Move '+validRows.length+' record(s) to History?',ui.ButtonSet.YES_NO);
  if (ok !== ui.Button.YES) return;

  var next = history.getLastRow() + 1;
  history.getRange(next,1,validRows.length,12).setValues(validRows);
  pending.getRange(3,1,lastRow-2,12).clearContent();
  logUpdate(ss,'Manual Approval');
  ui.alert('✅ Done! '+validRows.length+' record(s) saved to History.');
}

function logUpdate(ss, label) {
  var dash = ss.getSheetByName('Dashboard');
  var now  = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'MMM dd, yyyy  h:mm a');
  dash.getRange('B2').setValue(now).setFontStyle('normal').setFontColor('#212121');
  dash.getRange('E2').setValue(label||'Manual').setFontStyle('normal').setFontColor('#212121');
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 Portfolio Tools')
    .addItem('✅  Approve & Save Pending Data','approveAndSave')
    .addSeparator()
    .addItem('🔄  Refresh Dashboard Timestamp','refreshDashboard')
    .addToUi();
}

function refreshDashboard() {
  logUpdate(SpreadsheetApp.getActiveSpreadsheet(),'Manual Refresh');
  SpreadsheetApp.getUi().alert('Timestamp updated.');
}
// ── DASHBOARD + EMAIL + CHAT ENDPOINT ────────────────────────────
function doGet(e) {
  if (e && e.parameter && e.parameter.action === 'notify') {
    sendPendingReviewEmail();
    return ContentService.createTextOutput('OK').setMimeType(ContentService.MimeType.TEXT);
  }
  if (e && e.parameter && e.parameter.action === 'chat') {
    return handleChatRequest(e.parameter.q || '');
  }
  return getDashboardJson();
}

function getDashboardJson() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var data = { last_updated: new Date().toISOString(), llcs: [], history: [], loans: [], distributions: [], maintenance: [], settings: {} };

  var hist = ss.getSheetByName('History');
  var histLast = hist.getLastRow();
  if (histLast >= 2) {
    var histRows = hist.getRange(2, 1, histLast - 1, 12).getValues();
    histRows.forEach(function(r) {
      if (r[2]) {
        data.history.push({
          date_range: r[0],
          period_start: r[1] instanceof Date ? r[1].toISOString().slice(0,10) : r[1],
          llc: r[2],
          disbursement: Number(r[3]) || 0, mgmt_fee: Number(r[4]) || 0,
          mortgage: Number(r[5]) || 0, tax_mo: Number(r[6]) || 0,
          ins_mo: Number(r[7]) || 0, maintenance: Number(r[8]) || 0,
          net_cashflow: Number(r[9]) || 0, source: r[10],
          logged_at: r[11] instanceof Date ? r[11].toISOString() : r[11]
        });
      }
    });
  }

  var st = ss.getSheetByName('Settings');
  var stRows = st.getRange('A:E').getValues();
  stRows.forEach(function(r) {
    if (r[0] && r[1] !== '' && typeof r[1] === 'number') {
      data.llcs.push({
        name: r[0], monthly_mortgage: Number(r[1]) || 0,
        annual_tax: Number(r[2]) || 0, annual_insurance: Number(r[3]) || 0,
        property_value: Number(r[4]) || 0
      });
    }
  });

  var ln = ss.getSheetByName('Loans');
  var lnLast = ln.getLastRow();
  if (lnLast >= 5) {
    var lnRows = ln.getRange(5, 1, lnLast - 4, 12).getValues();
    lnRows.forEach(function(r) {
      if (r[0] && r[1]) {
        data.loans.push({
          llc: r[0], lender: r[1], loan_number: r[2], contact: r[3],
          original_balance: Number(r[4]) || 0, interest_rate: Number(r[5]) || 0,
          term_months: Number(r[6]) || 0,
          start_date: r[7] instanceof Date ? r[7].toISOString().slice(0,10) : r[7],
          monthly_payment: Number(r[8]) || 0,
          maturity_date: r[9] instanceof Date ? r[9].toISOString().slice(0,10) : r[9],
          balance_override: Number(r[10]) || 0, calculated_balance: Number(r[11]) || 0
        });
      }
    });
  }

  var dist = ss.getSheetByName('Distributions');
  if (dist) {
    var distLast = dist.getLastRow();
    if (distLast >= 5) {
      var distRows = dist.getRange(5, 1, distLast - 4, 5).getValues();
      distRows.forEach(function(r) {
        if (r[0]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          var yyyy = d.getFullYear();
          var mm = String(d.getMonth() + 1).padStart(2, '0');
          data.distributions.push({
            date_sent: d.toISOString().slice(0,10),
            period: yyyy + '-' + mm + '-01',
            llc: r[1] || "",
            your_amount: Number(r[2]) || 0,
            partner_amount: Number(r[3]) || 0,
            notes: r[4] || "",
          });
        }
      });
    }
  }

  var maint = ss.getSheetByName('Maintenance Log');
  if (maint) {
    var maintLast = maint.getLastRow();
    if (maintLast >= 5) {
      var maintRows = maint.getRange(5, 1, maintLast - 4, 5).getValues();
      maintRows.forEach(function(r) {
        if (r[0] && r[1]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          var yyyy = d.getFullYear();
          var mm = String(d.getMonth() + 1).padStart(2, '0');
          data.maintenance.push({
            date: d.toISOString().slice(0,10),
            period: yyyy + '-' + mm + '-01',
            llc: r[1],
            description: r[2] || "",
            amount: Number(r[3]) || 0,
            entered_by: r[4] || "",
          });
        }
      });
    }
  }

  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}

function sendPendingReviewEmail() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var pending = ss.getSheetByName('Pending Review');
  var st = ss.getSheetByName('Settings');
  var lastRow = pending.getLastRow();
  if (lastRow < 3) return;
  var data = pending.getRange(3, 1, lastRow - 2, 12).getValues();
  var rows = data.filter(function(r) { return r[0] !== '' && r[2] !== ''; });
  if (!rows.length) return;
  var toEmail = st.getRange('B13').getValue() || Session.getActiveUser().getEmail();
  var sheetUrl = ss.getUrl();
  var fmt = function(n) { return '$' + Number(n || 0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}); };
  var html = '<div style="font-family:-apple-system,Segoe UI,sans-serif;background:#f5f5f5;padding:20px">';
  html += '<div style="max-width:600px;margin:auto;background:white;border-radius:8px;padding:24px">';
  html += '<h2 style="color:#0c1a2e;margin:0 0 8px 0">📋 Niron Portfolio — Data Ready for Review</h2>';
  html += '<p style="color:#666">New monthly data has been pulled from AppFolio. Please review and approve.</p>';
  html += '<table style="width:100%;border-collapse:collapse;margin-bottom:20px">';
  html += '<tr style="background:#0c1a2e;color:white"><th style="padding:10px;text-align:left">LLC</th><th style="padding:10px;text-align:right">Disbursement</th><th style="padding:10px;text-align:right">Net Cashflow</th></tr>';
  rows.forEach(function(r) {
    var net = Number(r[9]) || 0;
    var color = net >= 0 ? '#007A33' : '#cc0033';
    html += '<tr style="border-bottom:1px solid #eee"><td style="padding:10px">' + r[2] + '</td>';
    html += '<td style="padding:10px;text-align:right">' + fmt(r[3]) + '</td>';
    html += '<td style="padding:10px;text-align:right;color:' + color + ';font-weight:600">' + fmt(net) + '</td></tr>';
  });
  html += '</table>';
  html += '<p style="text-align:center;margin:20px 0"><a href="' + sheetUrl + '" style="background:#0080cc;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:600">Open Sheet to Review →</a></p>';
  html += '</div></div>';
  MailApp.sendEmail({
    to: toEmail,
    subject: '📋 Niron Portfolio — ' + rows.length + ' record(s) ready for review',
    htmlBody: html
  });
}

function checkPendingReminder() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var pending = ss.getSheetByName('Pending Review');
  var st = ss.getSheetByName('Settings');
  var lastRow = pending.getLastRow();
  if (lastRow < 3) return;
  var data = pending.getRange(3, 1, lastRow - 2, 12).getValues();
  var rows = data.filter(function(r) { return r[0] !== '' && r[2] !== ''; });
  if (!rows.length) return;
  var now = new Date();
  var oldest = null;
  rows.forEach(function(r) {
    var d = r[11] instanceof Date ? r[11] : new Date(r[11]);
    if (!isNaN(d) && (!oldest || d < oldest)) oldest = d;
  });
  if (!oldest) return;
  var days = Math.floor((now - oldest) / (1000 * 60 * 60 * 24));
  if (days < 7) return;
  var toEmail = st.getRange('B13').getValue() || Session.getActiveUser().getEmail();
  var sheetUrl = ss.getUrl();
  MailApp.sendEmail({
    to: toEmail,
    subject: '⏰ Reminder — Portfolio data still pending review (' + days + ' days)',
    htmlBody: '<p>Your AppFolio portfolio data has been sitting in <b>Pending Review</b> for <b>' + days + ' days</b>.</p>' +
              '<p><a href="' + sheetUrl + '">Open the sheet</a> and use <b>Portfolio Tools → Approve & Save</b>.</p>'
  });
}

// ── CLAUDE CHATBOT ───────────────────────────────────────────────
function handleChatRequest(question) {
  if (!question) {
    return ContentService.createTextOutput(JSON.stringify({error: 'No question provided'}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    return ContentService.createTextOutput(JSON.stringify({error: 'API key not configured'}))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var context = buildPortfolioContext();
  var systemPrompt = 'You are a friendly real estate portfolio analyst. Answer questions about the user\'s rental property portfolio based ONLY on the data below. Be concise, friendly, and use bullet points for lists. Format dollar amounts like $X,XXX or $X.XK for large numbers. If something is not in the data, politely say so.\n\nPORTFOLIO DATA:\n' + context;

  var payload = {
    model: 'claude-haiku-4-5',
    max_tokens: 1024,
    system: systemPrompt,
    messages: [{role: 'user', content: question}]
  };

  var options = {
    method: 'POST',
    contentType: 'application/json',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', options);
    var result = JSON.parse(response.getContentText());
    if (result.error) {
      return ContentService.createTextOutput(JSON.stringify({error: result.error.message || 'API error'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    return ContentService.createTextOutput(JSON.stringify({
      answer: result.content[0].text,
      tokens: result.usage
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (e) {
    return ContentService.createTextOutput(JSON.stringify({error: 'Request failed: ' + e.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function buildPortfolioContext() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var summary = { history: [], settings: [], loans: [], distributions: [], maintenance: [] };

  var hist = ss.getSheetByName('History');
  var histLast = hist.getLastRow();
  if (histLast >= 2) {
    var histRows = hist.getRange(2, 1, histLast - 1, 12).getValues();
    histRows.forEach(function(r) {
      if (r[2]) {
        summary.history.push({
          month: r[1] instanceof Date ? Utilities.formatDate(r[1], Session.getScriptTimeZone(), 'MMM yyyy') : String(r[1]),
          llc: r[2],
          disbursement: Number(r[3]) || 0,
          mgmt_fees: Number(r[4]) || 0,
          mortgage: Number(r[5]) || 0,
          tax: Number(r[6]) || 0,
          insurance: Number(r[7]) || 0,
          maintenance: Number(r[8]) || 0,
          net: Number(r[9]) || 0
        });
      }
    });
  }

  var st = ss.getSheetByName('Settings');
  var stRows = st.getRange('A:E').getValues();
  stRows.forEach(function(r) {
    if (r[0] && typeof r[1] === 'number') {
      summary.settings.push({
        llc: r[0],
        monthly_mortgage: Number(r[1]),
        annual_tax: Number(r[2]),
        annual_insurance: Number(r[3]),
        property_value: Number(r[4])
      });
    }
  });

  var ln = ss.getSheetByName('Loans');
  var lnLast = ln.getLastRow();
  if (lnLast >= 5) {
    var lnRows = ln.getRange(5, 1, lnLast - 4, 12).getValues();
    lnRows.forEach(function(r) {
      if (r[0] && r[1]) {
        summary.loans.push({
          llc: r[0], lender: r[1],
          monthly_payment: Number(r[8]) || 0,
          remaining_balance: Number(r[10]) || Number(r[11]) || 0,
          maturity: r[9] instanceof Date ? Utilities.formatDate(r[9], Session.getScriptTimeZone(), 'yyyy-MM-dd') : String(r[9] || '')
        });
      }
    });
  }

  var dist = ss.getSheetByName('Distributions');
  if (dist) {
    var distLast = dist.getLastRow();
    if (distLast >= 5) {
      var distRows = dist.getRange(5, 1, distLast - 4, 5).getValues();
      distRows.forEach(function(r) {
        if (r[0]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          summary.distributions.push({
            date: Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd'),
            llc: r[1] || "",
            your_amount: Number(r[2]) || 0,
            partner_amount: Number(r[3]) || 0
          });
        }
      });
    }
  }

  var maint = ss.getSheetByName('Maintenance Log');
  if (maint) {
    var maintLast = maint.getLastRow();
    if (maintLast >= 5) {
      var maintRows = maint.getRange(5, 1, maintLast - 4, 5).getValues();
      maintRows.forEach(function(r) {
        if (r[0] && r[1]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          summary.maintenance.push({
            date: Utilities.formatDate(d, Session.getScriptTimeZone(), 'yyyy-MM-dd'),
            llc: r[1],
            description: r[2] || "",
            amount: Number(r[3]) || 0
          });
        }
      });
    }
  }

  return JSON.stringify(summary);
}

function authorizeApiAccess() {
  var result = handleChatRequest("test question");
  Logger.log(result.getContent());
}

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    if (body.action === 'chat' && body.messages) {
      return handleChatWithHistory(body.messages);
    }
  } catch (err) {}
  return ContentService.createTextOutput(JSON.stringify({error: 'Bad request'}))
    .setMimeType(ContentService.MimeType.JSON);
}

// Static, authoritative facts the chatbot should always know but that are not all
// stored in the Google Sheet (the fixed costs live in the dashboard code / CLAUDE.md).
// Keep these in sync with index.html constants and CLAUDE.md whenever a number changes.
function dashboardKnowledge() {
  return '=== DASHBOARD REFERENCE KNOWLEDGE ===\n'
    + 'NET CASHFLOW FORMULA (per LLC, per month): net = disbursement - mortgage - tax/12 - insurance/12 - maintenance.\n'
    + '  - disbursement = owner payout from the AppFolio Owner Packet (already net of management fees and supplies).\n'
    + '  - Divando property tax is paid as an ANNUAL April lump sum (about $31,620/yr, ~$2,635/mo): shown for reference but NOT subtracted from monthly net. Yale and Donald taxes are escrowed inside the mortgage, so their tax is $0 in net.\n'
    + '  - maintenance comes from the Maintenance Log.\n\n'
    + 'DIVANDO LLC -- total monthly debt = $14,533.86:\n'
    + '  - Property mortgages $12,199.86/mo across 6 building loans: 0210 $2,352.90 (15655 + 15675 E 13th Pl + 1310 Idalia), 0211 $1,718.36 (14790 E 43rd + 15559 Bates Lower/Upper), 0212 $2,315.84 (5538 Dearborn + 11795 Virginia), 0213 $2,014.78 (4776 Blackhawk + 5101 Crown A/B), 0214 $2,107.42 (3630 Holly + 2332 Oakland), 0215 $1,690.56 (3225 Tucson + 1724 Boston).\n'
    + '  - SBA loans $2,334.00/mo (6 drafts: $48 + $731 + $64 + $273 + $487 + $731) -- general business debt, NOT tied to any single property.\n'
    + '  - Insurance: State Farm $34,630/yr ($2,885.83/mo) across 13 units; Divando-owned share $29,677/yr. Agent Kevin Schult (303) 989-3847; renews Dec 15, 2026.\n'
    + '  - 3 out-of-state properties roll up under Divando, owned free and clear (NO mortgage/insurance), entered manually each month: 8222 Hare Ave (Jacksonville FL, Suncoast), 3899 Joest Rd and 6580 Stockport Dr (Memphis TN, Mid South).\n\n'
    + 'YALE TOWNHOMES, LLC -- 5 units (2991-2999 W Yale Ave, Denver): mortgage Lument $7,279.08/mo (/5 = $1,455.82/unit); insurance Acuity $1,037.55/mo (/5 = $207.51/unit); SBA loan $225/mo (LLC-level, not per-unit); tax escrowed.\n\n'
    + '5070 DONALD, LLC -- 8 units = 4 duplexes (5060-5082 E Donald Ave, Denver): mortgage CBRE $13,708.00/mo (/8 = $1,713.50/unit); insurance Westfield $1,210.84/mo (/8 = $151.36/unit); SBA loan $444/mo (LLC-level); tax escrowed.\n\n'
    + 'DORADO LLC -- only LLC-level totals are tracked (no per-unit breakdown yet). Owns 2397 Jamaica St and 4641 Enid Way, both insured on Divando\'s State Farm policy (Dorado credits $138/mo back to Divando; ends Dec 2026).\n\n'
    + 'MANUAL ENTRIES (Suncoast / Mid South): the owner enters the amount that actually hit the bank (the deposited amount), which can differ from the statement NOI. No mortgage/insurance, so net = amount entered.\n\n'
    + 'HOW THE DASHBOARD WORKS: The top cards show gross income, net cashflow and YTD, plus one card per LLC (each LLC card sums all of that LLC\'s History rows for the month, including the manual Suncoast/Mid South rows that roll up under Divando). The Per-Property Monitor lets you pick an LLC and a month and shows each unit\'s Income (Cash In), Disbursement, Repairs, Net, YTD Net and Occupancy (Divando, Yale and Donald are covered per-unit). Other tabs: History (LLC monthly cashflow), Loans, Distributions (Ron vs partner payouts), Maintenance Log (invoices, auto-deducted that month), and Noble Insurance (authoritative per-property insurance).\n';
}

function handleChatWithHistory(messages, activeTab, nobleContext) {
  if (!messages || !messages.length) {
    return ContentService.createTextOutput(JSON.stringify({error: 'No messages'}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var apiKey = PropertiesService.getScriptProperties().getProperty('ANTHROPIC_API_KEY');
  if (!apiKey) {
    return ContentService.createTextOutput(JSON.stringify({error: 'API key not configured'}))
      .setMimeType(ContentService.MimeType.JSON);
  }

  var context = buildPortfolioContext();
  var systemPrompt = 'You are a sharp, friendly real estate portfolio analyst for Ronen Moscovich (Ron), a Denver-based investor. You know his Niron portfolio inside and out.\n'
    + 'Answer using the data and reference knowledge below. Never say data is missing if it appears anywhere below.\n'
    + 'For totals / YTD / annual figures, READ the pre-computed summary tables -- do NOT re-add individual rows. For a specific month or unit, read the detail rows.\n'
    + '\nThe information below has FOUR sections:\n'
    + '  1. PORTFOLIO -- LLC-level monthly cashflow (History), annual totals, loans, distributions, maintenance.\n'
    + '  2. PROPERTY DETAIL -- per-UNIT monthly data for the individual addresses inside Divando LLC, Yale Townhomes LLC, and 5070 Donald LLC '
    + '(e.g. "5101 Crown Blvd Unit A", "2991 W Yale Ave", "5060 E Donald Ave"). Use this for ANY question about a specific address or unit.\n'
    + '  3. DASHBOARD REFERENCE KNOWLEDGE -- authoritative fixed costs (mortgages, SBA loans, taxes), the net-cashflow formula, manual-entry rules, and how the dashboard itself works.\n'
    + '  4. INSURANCE -- policies, renewal dates, premiums (Noble Insurance tab).\n'
    + '\nRULES:\n'
    + '- "Income" for a single property or unit = its Cash In (the dashboard\'s Income column). If asked for net, use Disbursement - Mortgage - Insurance/12 (tax is escrowed/annual, not in monthly net).\n'
    + '- A building/property can have several units (e.g. "Crown" = "5101 Crown Blvd Unit A" + "Unit B"; "Yale" = 5 units; "Donald" = 8 units). When asked about a whole property by name, SUM its units for each month before comparing months.\n'
    + '- For per-unit income/disbursement/occupancy use PROPERTY DETAIL. For insurance use INSURANCE. For fixed costs or "how does X work" use DASHBOARD REFERENCE KNOWLEDGE.\n'
    + '- This dashboard is NIRON only (Yale, Donald, Divando, Dorado). You have NO data on "Moss" -- it is a separate private portfolio; do not discuss or guess about it.\n'
    + '- Be concise and concrete. Use dollar amounts with commas. State the month/figures you used. No emojis unless Ron uses them first.\n\n'
    + context
    + '\n\n' + dashboardKnowledge();

  if (nobleContext && String(nobleContext).trim()) {
    systemPrompt += '\n\n=== INSURANCE DATA (Noble Insurance tab) ===\n' + nobleContext;
  }
  if (activeTab === 'noble') {
    systemPrompt += '\n\n[Ron is currently viewing the INSURANCE tab — prioritize insurance answers.]';
  }

  var payload = {
    model: 'claude-sonnet-4-6',
    max_tokens: 4096,
    // Cache the large data + reference context so multi-turn follow-ups are fast and cheap.
    system: [{ type: 'text', text: systemPrompt, cache_control: { type: 'ephemeral' } }],
    messages: messages
  };

  var options = {
    method: 'POST',
    contentType: 'application/json',
    headers: { 'x-api-key': apiKey, 'anthropic-version': '2023-06-01' },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  try {
    var response = UrlFetchApp.fetch('https://api.anthropic.com/v1/messages', options);
    var result = JSON.parse(response.getContentText());
    if (result.error) {
      return ContentService.createTextOutput(JSON.stringify({error: result.error.message || 'API error'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    return ContentService.createTextOutput(JSON.stringify({
      answer: result.content[0].text,
      tokens: result.usage
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (e) {
    return ContentService.createTextOutput(JSON.stringify({error: 'Request failed: ' + e.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
function buildPortfolioContext() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tz = ss.getSpreadsheetTimeZone();
  var summary = { history: [], settings: [], loans: [], distributions: [], maintenance: [] };

  function dateStr(v, fmt) {
    if (!(v instanceof Date)) return String(v || '');
    return Utilities.formatDate(v, tz, fmt || 'yyyy-MM-dd');
  }

  var hist = ss.getSheetByName('History');
  var histLast = hist.getLastRow();
  if (histLast >= 2) {
    var histRows = hist.getRange(2, 1, histLast - 1, 12).getValues();
    histRows.forEach(function(r) {
      if (r[2]) {
        summary.history.push({
          month: dateStr(r[1], 'yyyy-MM') + ' (' + dateStr(r[1], 'MMM yyyy') + ')',
          llc: r[2],
          disbursement: Number(r[3]) || 0,
          mgmt_fees: Number(r[4]) || 0,
          mortgage: Number(r[5]) || 0,
          tax: Number(r[6]) || 0,
          insurance: Number(r[7]) || 0,
          maintenance: Number(r[8]) || 0,
          net: Number(r[9]) || 0
        });
      }
    });
  }

  var st = ss.getSheetByName('Settings');
  var stRows = st.getRange('A:E').getValues();
  stRows.forEach(function(r) {
    if (r[0] && typeof r[1] === 'number') {
      summary.settings.push({
        llc: r[0],
        monthly_mortgage: Number(r[1]),
        annual_tax: Number(r[2]),
        annual_insurance: Number(r[3]),
        property_value: Number(r[4])
      });
    }
  });

  var ln = ss.getSheetByName('Loans');
  var lnLast = ln.getLastRow();
  if (lnLast >= 5) {
    var lnRows = ln.getRange(5, 1, lnLast - 4, 12).getValues();
    lnRows.forEach(function(r) {
      if (r[0] && r[1]) {
        summary.loans.push({
          llc: r[0], lender: r[1],
          monthly_payment: Number(r[8]) || 0,
          remaining_balance: Number(r[10]) || Number(r[11]) || 0,
          maturity: dateStr(r[9], 'yyyy-MM-dd')
        });
      }
    });
  }

  var dist = ss.getSheetByName('Distributions');
  if (dist) {
    var distLast = dist.getLastRow();
    if (distLast >= 5) {
      var distRows = dist.getRange(5, 1, distLast - 4, 5).getValues();
      distRows.forEach(function(r) {
        if (r[0]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          summary.distributions.push({
            date: dateStr(d, 'yyyy-MM-dd'),
            month: dateStr(d, 'MMM yyyy'),
            llc: r[1] || "",
            your_amount: Number(r[2]) || 0,
            partner_amount: Number(r[3]) || 0
          });
        }
      });
    }
  }

  var maint = ss.getSheetByName('Maintenance Log');
  if (maint) {
    var maintLast = maint.getLastRow();
    if (maintLast >= 5) {
      var maintRows = maint.getRange(5, 1, maintLast - 4, 5).getValues();
      maintRows.forEach(function(r) {
        if (r[0] && r[1]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          summary.maintenance.push({
            date: dateStr(d, 'yyyy-MM-dd'),
            month: dateStr(d, 'MMM yyyy'),
            llc: r[1],
            description: r[2] || "",
            amount: Number(r[3]) || 0
          });
        }
      });
    }
  }

  // Property Detail tab: per-property monthly data for Divando, Yale, Donald.
  // Columns: Date Range, Month, LLC, Property, Cash In, Rent Collected, Mgmt Fee,
  // Disbursement, Mortgage, Insurance/12, Status, Source, Updated.
  summary.property_detail = [];
  var pd = ss.getSheetByName('Property Detail');
  if (pd && pd.getLastRow() >= 2) {
    var pdRows = pd.getRange(2, 1, pd.getLastRow() - 1, 13).getValues();
    pdRows.forEach(function(r) {
      if (r[3]) {
        var pDate = r[1] instanceof Date ? dateStr(r[1], 'yyyy-MM') : String(r[1] || '').slice(0, 7);
        summary.property_detail.push({
          month: pDate,
          llc: r[2],
          property: r[3],
          cash_in: Number(r[4]) || 0,
          rent_collected: Number(r[5]) || 0,
          mgmt_fee: Number(r[6]) || 0,
          disbursement: Number(r[7]) || 0,
          mortgage: Number(r[8]) || 0,
          ins_mo: Number(r[9]) || 0,
          status: r[10] || ''
        });
      }
    });
  }

  return JSON.stringify(summary);
}
function rebuildMaintenanceLog() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Maintenance Log');
  if (!sh) { SpreadsheetApp.getUi().alert('Maintenance Log tab not found'); return; }

  sh.clear();
  sh.getRange('A1').setValue('🔧 MAINTENANCE LOG').setFontSize(18).setFontWeight('bold');
  sh.getRange('A2').setValue('Enter invoices anytime. Dashboard auto-deducts from net cashflow for that month.')
    .setFontStyle('italic');

  sh.getRange(4,1,1,7).setValues([['Date','LLC','Sub','Category','Description','Amount ($)','Entered By']])
    .setBackground('#1a1a2e').setFontColor('#ffffff').setFontWeight('bold').setHorizontalAlignment('center');
  sh.setFrozenRows(4);

  var dateRule = SpreadsheetApp.newDataValidation().requireDate().build();
  var llcRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Yale Townhomes, LLC','5070 Donald, LLC','Divando LLC','Dorado LLC'], true).build();
  var subRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Rigo','Samuel','Rolando','Tamir','Rudy','Rosalio','Melchor'], true)
    .setAllowInvalid(true).build();
  var catRule = SpreadsheetApp.newDataValidation()
    .requireValueInList([
      'Plumbing','Electrical','HVAC / AC','Appliances','Roof / Exterior',
      'Doors / Windows / Locks','Flooring / Walls / Paint','Pest / Mold',
      'Yard / Irrigation','Safety / Smoke Detectors','Tenant Turnover'
    ], true).build();

  sh.getRange('A5:A200').setDataValidation(dateRule).setNumberFormat('MM/dd/yyyy');
  sh.getRange('B5:B200').setDataValidation(llcRule);
  sh.getRange('C5:C200').setDataValidation(subRule);
  sh.getRange('D5:D200').setDataValidation(catRule);
  sh.getRange('F5:F200').setNumberFormat('$#,##0.00');

  [110,180,130,180,260,120,140].forEach(function(w,i){ sh.setColumnWidth(i+1,w); });

  SpreadsheetApp.getUi().alert('✅ Maintenance Log rebuilt!\n7 columns: Date | LLC | Sub | Category | Description | Amount | Entered By');
}
// === Override doPost to handle both chat AND adding maintenance ===
function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    if (body.action === 'chat' && body.messages) {
      return handleChatWithHistory(body.messages, body.active_tab, body.noble_context);
    }
    if (body.action === 'add_maintenance') {
      return addMaintenanceEntry(body);
    }
    if (body.action === 'update_maintenance') {
      return updateMaintenanceEntry(body);
    }
    if (body.action === 'delete_maintenance') {
      return deleteMaintenanceEntry(body);
    }
    if (body.action === 'set_maintenance_paid') {
      return setMaintenancePaid(body);
    }
    if (body.action === 'add_distribution') {
      return addDistributionEntry(body);
    }
    if (body.action === 'add_statement') {
      return addStatementEntry(body);
    }
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({error: 'Parse error: ' + err.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  return ContentService.createTextOutput(JSON.stringify({error: 'Bad request'}))
    .setMimeType(ContentService.MimeType.JSON);
}

function addMaintenanceEntry(data) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Maintenance Log');
  if (!sh) {
    return ContentService.createTextOutput(JSON.stringify({error: 'Maintenance Log not found'}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  if (!data.date || !data.llc || !data.amount) {
    return ContentService.createTextOutput(JSON.stringify({error: 'Date, LLC, and Amount are required'}))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var lastRow = sh.getLastRow();
  var nextRow = Math.max(5, lastRow + 1);
  var dateObj = new Date(data.date + 'T12:00:00');  // noon avoids timezone shifts
  sh.getRange(nextRow, 1, 1, 7).setValues([[
    dateObj,
    data.llc,
    data.sub || '',
    data.category || '',
    data.description || '',
    Number(data.amount) || 0,
    data.entered_by || 'Dashboard'
  ]]);
  return ContentService.createTextOutput(JSON.stringify({ok: true, row: nextRow}))
    .setMimeType(ContentService.MimeType.JSON);
}

// === Override getDashboardJson with new Maintenance Log structure (7 cols) ===
function getDashboardJson() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var data = { last_updated: new Date().toISOString(), llcs: [], history: [], loans: [], distributions: [], maintenance: [], settings: {} };

  var hist = ss.getSheetByName('History');
  var histLast = hist.getLastRow();
  if (histLast >= 2) {
    var histRows = hist.getRange(2, 1, histLast - 1, 12).getValues();
    histRows.forEach(function(r) {
      if (r[2]) {
        data.history.push({
          date_range: r[0],
          period_start: r[1] instanceof Date ? r[1].toISOString().slice(0,10) : r[1],
          llc: r[2],
          disbursement: Number(r[3]) || 0, mgmt_fee: Number(r[4]) || 0,
          mortgage: Number(r[5]) || 0, tax_mo: Number(r[6]) || 0,
          ins_mo: Number(r[7]) || 0, maintenance: Number(r[8]) || 0,
          net_cashflow: Number(r[9]) || 0, source: r[10],
          logged_at: r[11] instanceof Date ? r[11].toISOString() : r[11]
        });
      }
    });
  }

  var st = ss.getSheetByName('Settings');
  var stRows = st.getRange('A:E').getValues();
  stRows.forEach(function(r) {
    if (r[0] && r[1] !== '' && typeof r[1] === 'number') {
      data.llcs.push({
        name: r[0], monthly_mortgage: Number(r[1]) || 0,
        annual_tax: Number(r[2]) || 0, annual_insurance: Number(r[3]) || 0,
        property_value: Number(r[4]) || 0
      });
    }
  });

  var ln = ss.getSheetByName('Loans');
  var lnLast = ln.getLastRow();
  if (lnLast >= 5) {
    var lnRows = ln.getRange(5, 1, lnLast - 4, 12).getValues();
    lnRows.forEach(function(r) {
      if (r[0] && r[1]) {
        data.loans.push({
          llc: r[0], lender: r[1], loan_number: r[2], contact: r[3],
          original_balance: Number(r[4]) || 0, interest_rate: Number(r[5]) || 0,
          term_months: Number(r[6]) || 0,
          start_date: r[7] instanceof Date ? r[7].toISOString().slice(0,10) : r[7],
          monthly_payment: Number(r[8]) || 0,
          maturity_date: r[9] instanceof Date ? r[9].toISOString().slice(0,10) : r[9],
          balance_override: Number(r[10]) || 0, calculated_balance: Number(r[11]) || 0
        });
      }
    });
  }

  var dist = ss.getSheetByName('Distributions');
  if (dist) {
    var distLast = dist.getLastRow();
    if (distLast >= 5) {
      var distRows = dist.getRange(5, 1, distLast - 4, 5).getValues();
      distRows.forEach(function(r) {
        if (r[0]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          var yyyy = d.getFullYear();
          var mm = String(d.getMonth() + 1).padStart(2, '0');
          data.distributions.push({
            date_sent: d.toISOString().slice(0,10),
            period: yyyy + '-' + mm + '-01',
            llc: r[1] || "",
            your_amount: Number(r[2]) || 0,
            partner_amount: Number(r[3]) || 0,
            notes: r[4] || "",
          });
        }
      });
    }
  }

  // Maintenance — NEW 7-col structure: Date | LLC | Sub | Category | Description | Amount | Entered By
  var maint = ss.getSheetByName('Maintenance Log');
  if (maint) {
    var maintLast = maint.getLastRow();
    if (maintLast >= 5) {
      var maintRows = maint.getRange(5, 1, maintLast - 4, 7).getValues();
      maintRows.forEach(function(r) {
        if (r[0] && r[1]) {
          var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
          if (isNaN(d)) return;
          var yyyy = d.getFullYear();
          var mm = String(d.getMonth() + 1).padStart(2, '0');
          data.maintenance.push({
            date: d.toISOString().slice(0,10),
            period: yyyy + '-' + mm + '-01',
            llc: r[1],
            sub: r[2] || "",
            category: r[3] || "",
            description: r[4] || "",
            amount: Number(r[5]) || 0,
            entered_by: r[6] || "",
          });
        }
      });
    }
  }

  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}

// === Override buildPortfolioContext (for chatbot) with new Maintenance fields ===
function buildPortfolioContext() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tz = ss.getSpreadsheetTimeZone();

  function dateStr(v, fmt) {
    if (!(v instanceof Date)) return String(v || '').slice(0, 10);
    return Utilities.formatDate(v, tz, fmt || 'yyyy-MM-dd');
  }
  function dollar(n) { return '$' + Number(n).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

  // ── History ──────────────────────────────────────────────────────────────
  var rows = [];
  var hist = ss.getSheetByName('History');
  var histLast = hist ? hist.getLastRow() : 1;
  if (histLast >= 2) {
    hist.getRange(2, 1, histLast - 1, 12).getValues().forEach(function(r) {
      if (!r[2]) return;
      var ps = dateStr(r[1]);          // "2024-06-01" or "2024-06-01"
      var yr = ps.slice(0, 4);
      var mo = ps.slice(0, 7);         // "2024-06"
      rows.push({ yr: yr, mo: mo, llc: String(r[2]),
        disb: Number(r[3]) || 0, mgmt: Number(r[4]) || 0,
        mort: Number(r[5]) || 0, tax: Number(r[6]) || 0,
        ins: Number(r[7]) || 0, maint: Number(r[8]) || 0,
        net: Number(r[9]) || 0 });
    });
  }

  // ── Pre-compute annual totals (all LLCs combined) ─────────────────────
  var annTot = {};   // { "2024": { disb, net, months: Set } }
  var annLlc = {};   // { "2024": { "Yale...": { disb, net, months: Set } } }
  rows.forEach(function(r) {
    if (!annTot[r.yr]) annTot[r.yr] = { disb: 0, net: 0, mos: {} };
    annTot[r.yr].disb += r.disb;
    annTot[r.yr].net  += r.net;
    annTot[r.yr].mos[r.mo] = 1;

    if (!annLlc[r.yr]) annLlc[r.yr] = {};
    if (!annLlc[r.yr][r.llc]) annLlc[r.yr][r.llc] = { disb: 0, net: 0, mos: {} };
    annLlc[r.yr][r.llc].disb += r.disb;
    annLlc[r.yr][r.llc].net  += r.net;
    annLlc[r.yr][r.llc].mos[r.mo] = 1;
  });

  // ── Build readable context string ─────────────────────────────────────
  var years = Object.keys(annTot).sort();
  var allMos = rows.map(function(r){ return r.mo; });
  var earliest = allMos.length ? allMos.sort()[0] : 'N/A';
  var latest   = allMos.length ? allMos.sort().reverse()[0] : 'N/A';
  var llcNames = [];
  rows.forEach(function(r){ if (llcNames.indexOf(r.llc) < 0) llcNames.push(r.llc); });
  llcNames.sort();

  var ctx = '=== NIRON PORTFOLIO DATA ===\n';
  ctx += 'Data range: ' + earliest + ' through ' + latest + '\n';
  ctx += 'LLCs: ' + llcNames.join(', ') + '\n\n';

  ctx += '=== ANNUAL TOTALS (all LLCs combined) ===\n';
  years.forEach(function(yr) {
    var t = annTot[yr];
    var nMos = Object.keys(t.mos).length;
    ctx += yr + ': Gross Income ' + dollar(t.disb) + ' | Net Cashflow ' + dollar(t.net) + ' | ' + nMos + ' month(s) of data\n';
  });

  ctx += '\n=== PER-LLC ANNUAL TOTALS ===\n';
  years.forEach(function(yr) {
    ctx += yr + ':\n';
    Object.keys(annLlc[yr]).sort().forEach(function(llc) {
      var a = annLlc[yr][llc];
      var nMos = Object.keys(a.mos).length;
      ctx += '  ' + llc + ': Gross ' + dollar(a.disb) + ' | Net ' + dollar(a.net) + ' | ' + nMos + ' mo\n';
    });
  });

  ctx += '\n=== MONTHLY HISTORY (newest first) ===\n';
  ctx += 'Month     | LLC                    | Gross Income  | Net Cashflow  | Mortgage | Maintenance\n';
  rows.slice().sort(function(a,b){ return b.mo.localeCompare(a.mo); }).forEach(function(r) {
    ctx += r.mo + '  | ' + (r.llc + '                        ').slice(0,22) + ' | '
      + (dollar(r.disb) + '          ').slice(0,13) + ' | '
      + (dollar(r.net)  + '          ').slice(0,13) + ' | '
      + (dollar(r.mort) + '      ').slice(0,8) + ' | '
      + dollar(r.maint) + '\n';
  });

  // ── Loans ────────────────────────────────────────────────────────────────
  var ln = ss.getSheetByName('Loans');
  if (ln && ln.getLastRow() >= 5) {
    ctx += '\n=== LOANS ===\n';
    ln.getRange(5, 1, ln.getLastRow() - 4, 12).getValues().forEach(function(r) {
      if (r[0] && r[1]) {
        ctx += r[0] + ' | ' + r[1] + ' | payment ' + dollar(Number(r[8])||0)
          + ' | balance ' + dollar(Number(r[10])||Number(r[11])||0)
          + ' | maturity ' + dateStr(r[9]) + '\n';
      }
    });
  }

  // ── Distributions ────────────────────────────────────────────────────────
  var dist = ss.getSheetByName('Distributions');
  if (dist && dist.getLastRow() >= 5) {
    ctx += '\n=== DISTRIBUTIONS (Ron\'s share) ===\n';
    dist.getRange(5, 1, dist.getLastRow() - 4, 5).getValues().forEach(function(r) {
      if (!r[0]) return;
      var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
      if (isNaN(d)) return;
      ctx += dateStr(d) + ' | ' + (r[1]||'') + ' | Ron: ' + dollar(Number(r[2])||0) + ' | Nir: ' + dollar(Number(r[3])||0) + '\n';
    });
  }

  // ── Maintenance ──────────────────────────────────────────────────────────
  var maint = ss.getSheetByName('Maintenance Log');
  if (maint && maint.getLastRow() >= 5) {
    ctx += '\n=== MAINTENANCE LOG ===\n';
    maint.getRange(5, 1, maint.getLastRow() - 4, 7).getValues().forEach(function(r) {
      if (!r[0] || !r[1]) return;
      var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
      if (isNaN(d)) return;
      ctx += dateStr(d) + ' | ' + r[1] + ' | ' + (r[3]||'') + ' | ' + (r[4]||'') + ' | ' + dollar(Number(r[5])||0) + '\n';
    });
  }

  // ── Property Detail (per-UNIT monthly: Divando, Yale, Donald) ──────────────
  // Columns A-M: Date Range, Month, LLC, Property, Cash In, Rent Collected,
  // Mgmt Fee, Disbursement, Mortgage, Insurance/12, Status, Source, Updated.
  var pd = ss.getSheetByName('Property Detail');
  if (pd && pd.getLastRow() >= 2) {
    var pdRows = [];
    pd.getRange(2, 1, pd.getLastRow() - 1, 13).getValues().forEach(function(r) {
      if (!r[3]) return;
      var pmo = r[1] instanceof Date ? dateStr(r[1], 'yyyy-MM') : String(r[1] || '').slice(0, 7);
      pdRows.push({
        mo: pmo, llc: String(r[2]), prop: String(r[3]),
        cashIn: Number(r[4]) || 0, rent: Number(r[5]) || 0,
        disb: Number(r[7]) || 0, mort: Number(r[8]) || 0,
        ins: Number(r[9]) || 0, status: String(r[10] || '')
      });
    });

    if (pdRows.length) {
      // Per-unit aggregates so "highest / best / total" questions are reliable.
      var perProp = {};
      pdRows.forEach(function(p) {
        if (!perProp[p.prop]) perProp[p.prop] = { llc: p.llc, totCashIn: 0, totDisb: 0, bestMo: '', bestCashIn: -1, latestMo: '', latestStatus: '' };
        var a = perProp[p.prop];
        a.totCashIn += p.cashIn;
        a.totDisb += p.disb;
        if (p.cashIn > a.bestCashIn) { a.bestCashIn = p.cashIn; a.bestMo = p.mo; }
        if (p.mo > a.latestMo) { a.latestMo = p.mo; a.latestStatus = p.status; }
      });
      var pdLatest = pdRows.map(function(p){ return p.mo; }).sort().reverse()[0];

      ctx += '\n=== PROPERTY DETAIL (per-UNIT monthly: Divando, Yale, Donald) ===\n';
      ctx += 'Income for a unit = Cash In. Unit net = Disbursement - Mortgage - Insurance/12 (tax escrowed/annual). ';
      ctx += 'A building/property has multiple units (e.g. Crown = "5101 Crown Blvd Unit A" + "Unit B"); SUM its units per month when asked about the whole property. Latest month on file: ' + pdLatest + '.\n';

      ctx += '\n--- PER-UNIT SUMMARY (across all months on file) ---\n';
      Object.keys(perProp).sort().forEach(function(prop) {
        var a = perProp[prop];
        ctx += a.llc + ' | ' + prop
          + ' | highest Cash-In month: ' + a.bestMo + ' (' + dollar(a.bestCashIn) + ')'
          + ' | total Cash-In: ' + dollar(a.totCashIn)
          + ' | total Disbursement: ' + dollar(a.totDisb)
          + ' | latest ' + a.latestMo + ': ' + (a.latestStatus || 'n/a') + '\n';
      });

      ctx += '\n--- PER-UNIT MONTHLY ROWS (newest first) ---\n';
      ctx += 'Month   | Property                         | Cash In    | Rent       | Disburse   | Mortgage | Ins/mo  | Status\n';
      pdRows.sort(function(a, b){ return b.mo.localeCompare(a.mo) || a.prop.localeCompare(b.prop); }).forEach(function(p) {
        ctx += p.mo + ' | ' + (p.prop + '                                  ').slice(0, 32) + ' | '
          + (dollar(p.cashIn) + '          ').slice(0, 10) + ' | '
          + (dollar(p.rent)   + '          ').slice(0, 10) + ' | '
          + (dollar(p.disb)   + '          ').slice(0, 10) + ' | '
          + (dollar(p.mort)   + '        ').slice(0, 8) + ' | '
          + (dollar(p.ins)    + '       ').slice(0, 7) + ' | '
          + (p.status || '') + '\n';
      });
    }
  }

  return ctx;
}
function setupProperties() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Properties');
  if (!sh) sh = ss.insertSheet('Properties');
  sh.clear();

  sh.getRange('A1').setValue('🏠 PROPERTIES').setFontSize(18).setFontWeight('bold');
  sh.getRange('A2').setValue('Master list. Maintenance form picks property from here, auto-assigns the LLC.').setFontStyle('italic');

  sh.getRange(4, 1, 1, 3).setValues([['Address', 'LLC', 'Notes']])
    .setBackground('#1a1a2e').setFontColor('#ffffff').setFontWeight('bold').setHorizontalAlignment('center');
  sh.setFrozenRows(4);

  var properties = [
    ['2991 W Yale Ave, Denver CO', 'Yale Townhomes, LLC', 'Townhome unit'],
    ['2993 W Yale Ave, Denver CO', 'Yale Townhomes, LLC', 'Townhome unit'],
    ['2995 W Yale Ave, Denver CO', 'Yale Townhomes, LLC', 'Townhome unit'],
    ['2997 W Yale Ave, Denver CO', 'Yale Townhomes, LLC', 'Townhome unit'],
    ['2999 W Yale Ave, Denver CO', 'Yale Townhomes, LLC', 'Townhome unit'],
    ['5060 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['5062 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['5064 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['5066 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['5070 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['5072 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['5080 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['5082 E Donald Ave, Denver CO', '5070 Donald, LLC', 'Duplex unit'],
    ['14790 E 43rd Ave, Denver CO 80239', 'Divando LLC', ''],
    ['15559 E Bates Ave, Aurora CO 80013', 'Divando LLC', ''],
    ['15655 E 13th Ave, Aurora CO 80011', 'Divando LLC', 'Triplex unit'],
    ['15676 E 13th Ave, Aurora CO 80011', 'Divando LLC', 'Triplex unit'],
    ['1310 Idalia Ct, Aurora CO 80011', 'Divando LLC', 'Triplex unit'],
    ['1724 Boston St, Aurora CO 80010', 'Divando LLC', ''],
    ['2332 Oakland St, Aurora CO 80010', 'Divando LLC', ''],
    ['3225 Tucson St, Aurora CO 80011', 'Divando LLC', ''],
    ['3630 Holly St, Denver CO 80207', 'Divando LLC', ''],
    ['4776 Blackhawk Way, Denver CO 80239', 'Divando LLC', ''],
    ['5101 Crown Blvd, Denver CO 80239', 'Divando LLC', ''],
    ['5535 Dearborn St, Denver CO 80239', 'Divando LLC', ''],
    ['11795 E Virginia Dr, Aurora CO 80012', 'Divando LLC', ''],
    ['3899 Joest Dr, Memphis TN 38127', 'Divando LLC', 'Out-of-state — different portal (TBD)'],
    ['6580 Stockport Dr, Memphis TN 38141', 'Divando LLC', 'Out-of-state — different portal (TBD)'],
    ['8222 Hare Ave, Jacksonville FL 32211', 'Divando LLC', 'Out-of-state — different portal (TBD)'],
    ['2397 Jamaica St, Aurora CO 80010', 'Dorado LLC', ''],
    ['4641 Enid Way, Denver CO 80239', 'Dorado LLC', ''],
    ['1460 Unit A W 41st Ave, Denver CO 80211', 'Dorado LLC', 'Fourplex unit'],
    ['1460 Unit B W 41st Ave, Denver CO 80211', 'Dorado LLC', 'Fourplex unit'],
    ['1462 Unit A W 41st Ave, Denver CO 80211', 'Dorado LLC', 'Fourplex unit'],
    ['1462 Unit B W 41st Ave, Denver CO 80211', 'Dorado LLC', 'Fourplex unit']
  ];

  sh.getRange(5, 1, properties.length, 3).setValues(properties);

  var llcRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Yale Townhomes, LLC','5070 Donald, LLC','Divando LLC','Dorado LLC'], true).build();
  sh.getRange('B5:B200').setDataValidation(llcRule);

  sh.setColumnWidth(1, 320);
  sh.setColumnWidth(2, 200);
  sh.setColumnWidth(3, 280);

  SpreadsheetApp.getUi().alert('✅ Properties tab created with ' + properties.length + ' properties!');
}
function upgradeMaintenanceLog() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Maintenance Log');
  if (!sh) { SpreadsheetApp.getUi().alert('Maintenance Log not found'); return; }

  var lastRow = sh.getLastRow();
  var existingData = [];
  if (lastRow >= 5) {
    var oldRange = sh.getRange(5, 1, lastRow - 4, 7).getValues();
    oldRange.forEach(function(r) {
      if (r[0] && r[1]) {
        existingData.push([r[0], r[1], '', r[2], r[3], r[4], r[5], r[6]]);
      }
    });
  }

  sh.clear();
  sh.getRange('A1').setValue('🔧 MAINTENANCE LOG').setFontSize(18).setFontWeight('bold');
  sh.getRange('A2').setValue('Enter invoices. Dashboard auto-deducts from that month.').setFontStyle('italic');
  sh.getRange(4, 1, 1, 8).setValues([['Date','LLC','Property','Sub','Category','Description','Amount ($)','Entered By']])
    .setBackground('#1a1a2e').setFontColor('#ffffff').setFontWeight('bold').setHorizontalAlignment('center');
  sh.setFrozenRows(4);

  if (existingData.length) sh.getRange(5, 1, existingData.length, 8).setValues(existingData);

  var propsSheet = ss.getSheetByName('Properties');
  var properties = [];
  if (propsSheet && propsSheet.getLastRow() >= 5) {
    var propRows = propsSheet.getRange(5, 1, propsSheet.getLastRow() - 4, 1).getValues();
    properties = propRows.map(function(r) { return r[0]; }).filter(function(r) { return r; });
  }

  var dateRule = SpreadsheetApp.newDataValidation().requireDate().build();
  var llcRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Yale Townhomes, LLC','5070 Donald, LLC','Divando LLC','Dorado LLC'], true).build();
  var subRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Rigo','Samuel','Rolando','Tamir','Rudy','Rosalio','Melchor'], true).setAllowInvalid(true).build();
  var catRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['Plumbing','Electrical','HVAC / AC','Appliances','Roof / Exterior','Doors / Windows / Locks','Flooring / Walls / Paint','Pest / Mold','Yard / Irrigation','Safety / Smoke Detectors','Tenant Turnover'], true).build();

  sh.getRange('A5:A200').setDataValidation(dateRule).setNumberFormat('MM/dd/yyyy');
  sh.getRange('B5:B200').setDataValidation(llcRule);
  if (properties.length) {
    var propRule = SpreadsheetApp.newDataValidation().requireValueInList(properties, true).setAllowInvalid(true).build();
    sh.getRange('C5:C200').setDataValidation(propRule);
  }
  sh.getRange('D5:D200').setDataValidation(subRule);
  sh.getRange('E5:E200').setDataValidation(catRule);
  sh.getRange('G5:G200').setNumberFormat('$#,##0.00');

  [110,180,220,130,180,260,120,140].forEach(function(w,i){ sh.setColumnWidth(i+1,w); });

  SpreadsheetApp.getUi().alert('✅ Maintenance Log upgraded!\nPreserved ' + existingData.length + ' existing entries.');
}

// Override: new addMaintenanceEntry with Property column
function addMaintenanceEntry(data) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Maintenance Log');
  if (!sh) return ContentService.createTextOutput(JSON.stringify({error:'Maintenance Log not found'})).setMimeType(ContentService.MimeType.JSON);
  if (!data.date || !data.llc || !data.amount) return ContentService.createTextOutput(JSON.stringify({error:'Date, LLC, Amount required'})).setMimeType(ContentService.MimeType.JSON);
  var lastRow = sh.getLastRow();
  var nextRow = Math.max(5, lastRow + 1);
  var dateObj = new Date(data.date + 'T12:00:00');
  var invoiceUrl = '';
  if (data.file && data.file.data) {
    try { invoiceUrl = saveInvoiceFile(data.file); }
    catch (err) { return ContentService.createTextOutput(JSON.stringify({error:'File upload failed: ' + err.message})).setMimeType(ContentService.MimeType.JSON); }
  }
  // Columns A-L: Date, LLC, Property, Sub, Category, Description, Amount, Entered By,
  //              Paid By, Paid, Notes, Invoice File URL
  sh.getRange(nextRow, 1, 1, 12).setValues([[
    dateObj, data.llc, data.property || '', data.sub || '',
    data.category || '', data.description || '',
    Number(data.amount) || 0, data.entered_by || 'Dashboard',
    data.paid_by || '', data.paid ? true : false, data.notes || '', invoiceUrl
  ]]);
  return ContentService.createTextOutput(JSON.stringify({ok:true, row:nextRow, invoice_url:invoiceUrl})).setMimeType(ContentService.MimeType.JSON);
}

// Edit an existing maintenance invoice in place. `row` is the absolute sheet row
// (sent by the dashboard, originally from getDashboardJson's maintenance.row).
function updateMaintenanceEntry(data) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Maintenance Log');
  if (!sh) return ContentService.createTextOutput(JSON.stringify({error:'Maintenance Log not found'})).setMimeType(ContentService.MimeType.JSON);
  var row = Number(data.row);
  if (!row || row < 5 || row > sh.getLastRow()) return ContentService.createTextOutput(JSON.stringify({error:'Invalid row'})).setMimeType(ContentService.MimeType.JSON);
  if (!data.date || !data.llc || !data.amount) return ContentService.createTextOutput(JSON.stringify({error:'Date, LLC, Amount required'})).setMimeType(ContentService.MimeType.JSON);
  var dateObj = new Date(data.date + 'T12:00:00');
  // Keep the existing invoice link unless a new file is uploaded.
  var invoiceUrl = sh.getRange(row, 12).getValue() || '';
  if (data.file && data.file.data) {
    try { invoiceUrl = saveInvoiceFile(data.file); }
    catch (err) { return ContentService.createTextOutput(JSON.stringify({error:'File upload failed: ' + err.message})).setMimeType(ContentService.MimeType.JSON); }
  }
  sh.getRange(row, 1, 1, 12).setValues([[
    dateObj, data.llc, data.property || '', data.sub || '',
    data.category || '', data.description || '',
    Number(data.amount) || 0, data.entered_by || 'Dashboard',
    data.paid_by || '', data.paid ? true : false, data.notes || '', invoiceUrl
  ]]);
  return ContentService.createTextOutput(JSON.stringify({ok:true, row:row, invoice_url:invoiceUrl})).setMimeType(ContentService.MimeType.JSON);
}

// Delete a maintenance invoice row entirely.
function deleteMaintenanceEntry(data) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Maintenance Log');
  if (!sh) return ContentService.createTextOutput(JSON.stringify({error:'Maintenance Log not found'})).setMimeType(ContentService.MimeType.JSON);
  var row = Number(data.row);
  if (!row || row < 5 || row > sh.getLastRow()) return ContentService.createTextOutput(JSON.stringify({error:'Invalid row'})).setMimeType(ContentService.MimeType.JSON);
  sh.deleteRow(row);
  return ContentService.createTextOutput(JSON.stringify({ok:true, deleted:row})).setMimeType(ContentService.MimeType.JSON);
}

// Flip just the Paid column (J) for a row - used by the CPA view's one-click "Mark paid".
function setMaintenancePaid(data) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Maintenance Log');
  if (!sh) return ContentService.createTextOutput(JSON.stringify({error:'Maintenance Log not found'})).setMimeType(ContentService.MimeType.JSON);
  var row = Number(data.row);
  if (!row || row < 5 || row > sh.getLastRow()) return ContentService.createTextOutput(JSON.stringify({error:'Invalid row'})).setMimeType(ContentService.MimeType.JSON);
  sh.getRange(row, 10).setValue(data.paid ? true : false);
  return ContentService.createTextOutput(JSON.stringify({ok:true, row:row, paid:!!data.paid})).setMimeType(ContentService.MimeType.JSON);
}

// Save an uploaded invoice file to a dedicated Drive folder; return its view URL.
// file = { name, mimeType, data(base64) }. Set link-viewable so the URL opens from the
// dashboard and the CPA export. (Adds a Drive scope - reauthorize on redeploy.)
function saveInvoiceFile(file) {
  var folders = DriveApp.getFoldersByName('Niron Maintenance Invoices');
  var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder('Niron Maintenance Invoices');
  var bytes = Utilities.base64Decode(file.data);
  var blob = Utilities.newBlob(bytes, file.mimeType || 'application/octet-stream', file.name || 'invoice');
  var f = folder.createFile(blob);
  try { f.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW); } catch (e) {}
  return f.getUrl();
}

// Override: getDashboardJson with properties + new maintenance structure
function getDashboardJson() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var data = { last_updated: new Date().toISOString(), llcs: [], history: [], loans: [], distributions: [], maintenance: [], properties: [], property_detail: [], settings: {} };

  // Track the most-recent real data-change timestamp (History "Logged At" + Property
  // Detail "Updated"), so the dashboard's "Last Updated" reflects when the data last
  // actually changed - not when this page happened to load.
  var lastChange = null;
  function bumpChange(v) { if (v instanceof Date && !isNaN(v.getTime()) && (!lastChange || v > lastChange)) lastChange = v; }

  var hist = ss.getSheetByName('History');
  var histLast = hist.getLastRow();
  if (histLast >= 2) {
    var histRows = hist.getRange(2, 1, histLast - 1, 12).getValues();
    histRows.forEach(function(r) {
      if (r[2]) bumpChange(r[11]);
      if (r[2]) data.history.push({
        date_range: r[0],
        period_start: r[1] instanceof Date ? r[1].toISOString().slice(0,10) : r[1],
        llc: r[2], disbursement: Number(r[3])||0, mgmt_fee: Number(r[4])||0,
        mortgage: Number(r[5])||0, tax_mo: Number(r[6])||0,
        ins_mo: Number(r[7])||0, maintenance: Number(r[8])||0,
        net_cashflow: Number(r[9])||0, source: r[10],
        logged_at: r[11] instanceof Date ? r[11].toISOString() : r[11]
      });
    });
  }

  ss.getSheetByName('Settings').getRange('A:E').getValues().forEach(function(r) {
    if (r[0] && r[1] !== '' && typeof r[1] === 'number') {
      data.llcs.push({ name: r[0], monthly_mortgage: Number(r[1])||0,
        annual_tax: Number(r[2])||0, annual_insurance: Number(r[3])||0,
        property_value: Number(r[4])||0 });
    }
  });

  var ln = ss.getSheetByName('Loans');
  if (ln && ln.getLastRow() >= 5) {
    ln.getRange(5, 1, ln.getLastRow() - 4, 12).getValues().forEach(function(r) {
      if (r[0] && r[1]) data.loans.push({
        llc: r[0], lender: r[1], loan_number: r[2], contact: r[3],
        original_balance: Number(r[4])||0, interest_rate: Number(r[5])||0,
        term_months: Number(r[6])||0,
        start_date: r[7] instanceof Date ? r[7].toISOString().slice(0,10) : r[7],
        monthly_payment: Number(r[8])||0,
        maturity_date: r[9] instanceof Date ? r[9].toISOString().slice(0,10) : r[9],
        balance_override: Number(r[10])||0, calculated_balance: Number(r[11])||0
      });
    });
  }

  var dist = ss.getSheetByName('Distributions');
  if (dist && dist.getLastRow() >= 5) {
    dist.getRange(5, 1, dist.getLastRow() - 4, 5).getValues().forEach(function(r) {
      if (r[0]) {
        var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
        if (isNaN(d)) return;
        var yyyy = d.getFullYear(); var mm = String(d.getMonth()+1).padStart(2,'0');
        data.distributions.push({
          date_sent: d.toISOString().slice(0,10),
          period: yyyy + '-' + mm + '-01', llc: r[1] || "",
          your_amount: Number(r[2])||0, partner_amount: Number(r[3])||0,
          notes: r[4] || ""
        });
      }
    });
  }

  var maint = ss.getSheetByName('Maintenance Log');
  if (maint && maint.getLastRow() >= 5) {
    // Track the absolute sheet row (data starts at row 5) so the dashboard can
    // edit/delete the exact row via update_maintenance / delete_maintenance.
    // Columns A-L: Date, LLC, Property, Sub, Category, Description, Amount, Entered By,
    //              Paid By (I/8), Paid (J/9), Notes (K/10), Invoice File URL (L/11).
    maint.getRange(5, 1, maint.getLastRow() - 4, 12).getValues().forEach(function(r, i) {
      if (r[0] && r[1]) {
        var d = r[0] instanceof Date ? r[0] : new Date(r[0]);
        if (isNaN(d)) return;
        var yyyy = d.getFullYear(); var mm = String(d.getMonth()+1).padStart(2,'0');
        data.maintenance.push({
          row: 5 + i,
          date: d.toISOString().slice(0,10),
          period: yyyy + '-' + mm + '-01',
          llc: r[1], property: r[2] || "", sub: r[3] || "",
          category: r[4] || "", description: r[5] || "",
          amount: Number(r[6])||0, entered_by: r[7] || "",
          paid_by: r[8] || "", paid: r[9] === true || String(r[9]).toLowerCase() === 'true',
          notes: r[10] || "", invoice_url: r[11] || ""
        });
      }
    });
  }

  var props = ss.getSheetByName('Properties');
  if (props && props.getLastRow() >= 5) {
    props.getRange(5, 1, props.getLastRow() - 4, 3).getValues().forEach(function(r) {
      if (r[0] && r[1]) data.properties.push({
        address: r[0], llc: r[1], notes: r[2] || ""
      });
    });
  }

  // Property Detail tab — per-property monthly rows written by run_divando.py /
  // backfill_divando.py (Divando units) and run_yale.py / backfill_yale.py (Yale
  // townhome units). Read generically by LLC, so new LLCs flow through with no edit
  // here. Header in row 1, data from row 2. Columns (A-M):
  // Date Range, Month, LLC, Property, Cash In, Rent Collected, Mgmt Fee,
  // Disbursement, Mortgage, Insurance/12, Status, Source, Updated.
  var pd = ss.getSheetByName('Property Detail');
  if (pd && pd.getLastRow() >= 2) {
    pd.getRange(2, 1, pd.getLastRow() - 1, 13).getValues().forEach(function(r) {
      if (r[3]) bumpChange(r[12]);
      if (r[3]) data.property_detail.push({
        date_range: r[0],
        period_start: r[1] instanceof Date ? r[1].toISOString().slice(0,10) : r[1],
        llc: r[2], property: r[3],
        cash_in: Number(r[4])||0, rent_collected: Number(r[5])||0,
        mgmt_fee: Number(r[6])||0, disbursement: Number(r[7])||0,
        mortgage: Number(r[8])||0, ins_mo: Number(r[9])||0,
        status: r[10] || "", source: r[11] || "",
        updated: r[12] instanceof Date ? r[12].toISOString() : r[12]
      });
    });
  }

  // Honest "Last Updated": the latest real write timestamp, falling back to now only
  // if no timestamps exist yet.
  data.last_updated = lastChange ? lastChange.toISOString() : new Date().toISOString();
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}

function addDistributionEntry(data) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Distributions');
  if (!sh) return ContentService.createTextOutput(JSON.stringify({error:'Distributions tab not found'})).setMimeType(ContentService.MimeType.JSON);
  if (!data.date || !data.llc) return ContentService.createTextOutput(JSON.stringify({error:'Date and LLC required'})).setMimeType(ContentService.MimeType.JSON);
  var dateObj = new Date(data.date + 'T12:00:00');
  var yourA = Number(data.your_amount) || 0;
  var partA = Number(data.partner_amount) || 0;
  // Duplicate guard: same LLC + same month + same amounts already recorded.
  // Prevents a double-click or re-entry from inflating Your Distribution / YTD.
  function distPeriod(d) { return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2); }
  var newPeriod = distPeriod(dateObj);
  var lastRow = sh.getLastRow();
  if (lastRow >= 5) {
    var existing = sh.getRange(5, 1, lastRow - 4, 4).getValues();
    for (var i = 0; i < existing.length; i++) {
      var ed = existing[i][0] instanceof Date ? existing[i][0] : new Date(existing[i][0]);
      if (isNaN(ed)) continue;
      if (distPeriod(ed) === newPeriod && String(existing[i][1]) === String(data.llc) &&
          (Number(existing[i][2]) || 0) === yourA && (Number(existing[i][3]) || 0) === partA) {
        return ContentService.createTextOutput(JSON.stringify({error: 'Already recorded a ' + data.llc + ' distribution for ' + newPeriod + ' with the same amounts.'})).setMimeType(ContentService.MimeType.JSON);
      }
    }
  }
  var nextRow = Math.max(5, lastRow + 1);
  sh.getRange(nextRow, 1, 1, 5).setValues([[
    dateObj,
    data.llc,
    Number(data.your_amount) || 0,
    Number(data.partner_amount) || 0,
    data.notes || ''
  ]]);
  sh.getRange(nextRow, 3, 1, 2).setNumberFormat('$#,##0.00');
  return ContentService.createTextOutput(JSON.stringify({ok: true, row: nextRow})).setMimeType(ContentService.MimeType.JSON);
}

// === Add a monthly statement row (Suncoast / MidSouth Propertyware properties) ===
// Writes one row to the History tab. No mortgage / no insurance -> net cashflow == NOI.
function addStatementEntry(data) {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('History');
  if (!sh) return ContentService.createTextOutput(JSON.stringify({error:'History tab not found'})).setMimeType(ContentService.MimeType.JSON);
  if (!data.month || !data.property) return ContentService.createTextOutput(JSON.stringify({error:'Month and Property required'})).setMimeType(ContentService.MimeType.JSON);

  var noi = Number(data.noi) || 0;
  if (!noi) return ContentService.createTextOutput(JSON.stringify({error:'NOI must be a non-zero number'})).setMimeType(ContentService.MimeType.JSON);

  // Parse "YYYY-MM"
  var parts = String(data.month).split('-');
  var year = parseInt(parts[0], 10);
  var month = parseInt(parts[1], 10);
  if (!year || !month) return ContentService.createTextOutput(JSON.stringify({error:'Month must look like 2026-04'})).setMimeType(ContentService.MimeType.JSON);
  var lastDay = new Date(year, month, 0).getDate();
  function pad(n){ return ('0' + n).slice(-2); }
  var periodStart = year + '-' + pad(month) + '-01';
  var dateRange = pad(month) + '/01/' + year + ' - ' + pad(month) + '/' + pad(lastDay) + '/' + year;

  // These 3 Propertyware properties roll up under Divando LLC, but we keep the
  // property name in the Source column so each one is still distinguishable
  // (and so the duplicate-check lets all 3 be entered for the same month).
  var llc = 'Divando LLC';
  var source = 'Manual Entry: ' + data.property;

  // Duplicate check: same period_start (col B) + same Source (col K)
  var lastRow = sh.getLastRow();
  if (lastRow >= 2) {
    var existing = sh.getRange(2, 1, lastRow - 1, 11).getValues();
    for (var i = 0; i < existing.length; i++) {
      var ps = existing[i][1] instanceof Date ? existing[i][1].toISOString().slice(0,10) : String(existing[i][1]);
      if (ps === periodStart && String(existing[i][10]) === source) {
        return ContentService.createTextOutput(JSON.stringify({error: 'Already recorded ' + data.property + ' for ' + periodStart})).setMimeType(ContentService.MimeType.JSON);
      }
    }
  }

  // History columns: Date Range | Period Start | LLC | Disbursements | Mgmt Fees | Mortgage | Tax/12 | Ins/12 | Maintenance | Net Cashflow | Source | Logged At
  var loggedAt = Utilities.formatDate(new Date(), 'America/Denver', 'yyyy-MM-dd HH:mm:ss');
  var nextRow = lastRow + 1;
  sh.getRange(nextRow, 1, 1, 12).setValues([[
    dateRange, periodStart, llc,
    noi, 0,        // disbursement (= NOI), mgmt fee
    0, 0, 0,       // mortgage, tax/12, ins/12
    0, noi,        // maintenance, net cashflow
    source, loggedAt
  ]]);
  return ContentService.createTextOutput(JSON.stringify({ok: true, row: nextRow, message: 'Saved ' + data.property + ' (Divando LLC) ' + periodStart})).setMimeType(ContentService.MimeType.JSON);
}
