$subcircuit = "STRCIRCUITDATAFOLDER";
$iter=ITERNUM;
$replacement=REPLACEMENTNUM;
%redact = (  
STRSUBCKTANDINPUTOUTPUT
);
@subckts=keys %redact;

open(fh1,"<", "$subcircuit/sub_circuit/iter$iter/top.v") or  die "can not open file";
open(fh2,">", "$subcircuit/sub_circuit/iter$iter/top_obf.v") or  die "can not open file";
$keysizeL = 0;
while(<fh1>) {
  if (/module\s+top\((.*)\)/) {
    print fh2 "module top_obf($1, keyinput);\n";
  } elsif(!/endmodule/) {
  if (/(sub_ckt_\d+)\s+(inst_sub_ckt_\d+)\((.*)\);/) {
    if (grep { $1 eq $_ } @subckts) {
      @io=split ' ', $redact{$1};
      $keysizeR = $keysizeL;
      $keysizeL = (2 ** $io[0]) * $io[1] + $keysizeL;
      print fh2 "lut_$io[0]_$io[1] $2(";
      @ports = $3 =~ /\((\S+)\)/g;
      $i=0;
      foreach(@ports) {
        if ($i < $io[0]) { print fh2 ".in${i}($_), "}
        if ($i >= $io[0]) { $j = $i-$io[0]; print fh2 ".out$j($_), "}
        $i=$i+1;
      }
      $keysizeL2 = $keysizeL - 1;
      print fh2 ".prog_key(keyinput[$keysizeL2:$keysizeR]));";
    } else { print fh2 $_;}
  } else { print fh2 $_;}
  }
  if (/endmodule/){print fh2 "input [$keysizeL2:0] keyinput;\n"; print fh2 $_}
}
close fh1;
close fh2;

open(fh3,"<", "read_$iter.tcl") or  die "can not open file";
open(fh4,">", "./tmp.tcl") or  die "can not open file";
while(<fh3>) {
  if(/sub_circuit\/iter$iter\/(sub_ckt_\d+)\/(sub_ckt_\d+)/) {
    if (grep { $1 eq $_ } @subckts) {
      @io=split ' ', $redact{$1};
      print fh4 "RTLLUTROOT/lut_$io[0]_$io[1].v\n";
    } else { print fh4 $_;} 
  } elsif(/sub_circuit\/iter$iter\/top.v/) { print fh4 "$subcircuit/sub_circuit/iter$iter/top_obf.v\n";}
  else { print fh4 $_;}
}
close fh3;
close fh4;
$tmp=`cat -n ./tmp.tcl | sort -uk2 | sort -n | cut -f2- > INTERMEDIATEFOLDERPATH/read_obf_ITERNUM.tcl`;
print $tmp;
$tmp =`rm ./tmp.tcl`;
print $tmp;
