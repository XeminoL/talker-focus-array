`timescale 1ns / 1ps

module fir_decimator_tb;

    parameter SAMPLES = 3000;
    parameter GAP = 150;

    reg clk = 1'b0;
    reg rst = 1'b1;
    reg in_valid = 1'b0;
    reg signed [23:0] in_sample = 0;
    wire out_valid;
    wire signed [23:0] out_sample;

    reg [23:0] stimulus [0:SAMPLES-1];
    integer index;
    integer outputs;
    integer file;

    fir_decimator dut (
        .clk(clk),
        .rst(rst),
        .in_valid(in_valid),
        .in_sample(in_sample),
        .out_valid(out_valid),
        .out_sample(out_sample)
    );

    always #4 clk = ~clk;

    always @(posedge clk) begin
        if (out_valid) begin
            $fdisplay(file, "%0d", out_sample);
            outputs = outputs + 1;
        end
    end

    initial begin
        $readmemh("fir_stimulus.hex", stimulus);
        file = $fopen("fir_rtl.txt", "w");
        outputs = 0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        for (index = 0; index < SAMPLES; index = index + 1) begin
            @(posedge clk);
            in_valid  <= 1'b1;
            in_sample <= stimulus[index];
            @(posedge clk);
            in_valid  <= 1'b0;
            repeat (GAP) @(posedge clk);
        end
        repeat (200) @(posedge clk);
        $fclose(file);
        $display("outputs %0d", outputs);
        $finish;
    end

endmodule
