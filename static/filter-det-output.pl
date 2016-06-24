
# with this code, i modified the output from det.embl.de into enrichment-example2.txt. 
#  all annotations for these chemicals were printed.
# here the focus is only on the enriched terms so we filter accordingly. 
open FILE,"example-table.txt";
while(<FILE>)
{
	chomp $_;
	@p=split("\t",$_);
	$v{$p[0]}=1;
}
close FILE;

open FILE,"enrichment-example.txt";
open NEW,">enrichment-example2.txt";
while(<FILE>)
{
	chomp $_;
	@p=split("\t",$_);
	@n=split("; ",$p[2]);
	for($i=0;$i<scalar @n;$i++)
	{
		if($v{$n[$i]}==1)
		{
			print NEW $n[$i],"\t",$p[0],"\n";
		}
	}
	
}
close FILE;
close NEW;