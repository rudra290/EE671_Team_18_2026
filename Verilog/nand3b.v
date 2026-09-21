module nand3b (
    input  wire a,
    input  wire b,
    input  wire c,
    output wire out
);

assign out = ~((~a) & b & c);

endmodule
