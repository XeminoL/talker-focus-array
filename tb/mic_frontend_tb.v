`timescale 1ns / 1ps

module mic_frontend_tb;

    parameter CHANNELS = 64;
    parameter TICKS = 19200;
    parameter TICK_CYCLES = 40;

    reg clk = 1'b0;
    reg rst = 1'b1;
    reg pdm_valid = 1'b0;
    reg [CHANNELS-1:0] pdm_bits = 0;
    wire out_valid;
    wire [5:0] out_channel;
    wire signed [23:0] out_sample;

    reg [CHANNELS-1:0] stimulus [0:TICKS-1];
    integer tick;
    integer outputs;
    integer file;

    mic_frontend dut (
        .clk(clk),
        .rst(rst),
        .pdm_valid(pdm_valid),
        .pdm_bits(pdm_bits),
        .out_valid(out_valid),
        .out_channel(out_channel),
        .out_sample(out_sample)
    );

    always #4 clk = ~clk;

    always @(posedge clk) begin
        if (out_valid) begin
            $fdisplay(file, "%0d %0d", out_channel, out_sample);
            outputs = outputs + 1;
        end
    end

    initial begin
        $readmemh("frontend_stimulus.hex", stimulus);
        file = $fopen("frontend_rtl.txt", "w");
        outputs = 0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        for (tick = 0; tick < TICKS; tick = tick + 1) begin
            @(posedge clk);
            pdm_valid <= 1'b1;
            pdm_bits  <= stimulus[tick];
            @(posedge clk);
            pdm_valid <= 1'b0;
            repeat (TICK_CYCLES - 2) @(posedge clk);
        end
        repeat (TICK_CYCLES * 64 * 4) @(posedge clk);
        $fclose(file);
        $display("outputs %0d", outputs);
        $finish;
    end

endmodule
