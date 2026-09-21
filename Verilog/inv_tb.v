`timescale 1ns/1ps

module inv_tb;
reg vin;
wire vout;

inv dut (
    .vin(vin),
    .vout(vout)
);

initial begin
    vin = 1'b0;
    #1;
    if (vout !== 1'b1) $fatal(1, "vin=0 failed");
    vin = 1'b1;
    #1;
    if (vout !== 1'b0) $fatal(1, "vin=1 failed");
    $display("inv functional test passed");
    $finish;
end
endmodule
