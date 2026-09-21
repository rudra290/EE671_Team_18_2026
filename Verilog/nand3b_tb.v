`timescale 1ns/1ps

module nand3b_tb;

reg a, b, c;
wire out;
reg expected;
integer i;

nand3b dut (
    .a(a),
    .b(b),
    .c(c),
    .out(out)
);

initial begin
    for (i = 0; i < 8; i = i + 1) begin
        {a, b, c} = i[2:0];
        expected = (i != 3);
        #1;

        if (out !== expected)
            $fatal(1, "FAIL: ABC=%b%b%b OUT=%b expected=%b",
                   a, b, c, out, expected);

        $display("PASS: ABC=%b%b%b OUT=%b", a, b, c, out);
    end

    $display("All 8 NAND3B combinations passed.");
    $finish;
end

endmodule
