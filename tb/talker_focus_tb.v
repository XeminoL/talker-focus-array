`timescale 1ns / 1ps

module talker_focus_tb;

    parameter CHANNELS = 64;
    parameter TAPS = 64;
    parameter TICKS = 38400;
    parameter TICK_CYCLES = 40;
    parameter SHIFT = 20;

    reg clk = 1'b0;
    reg rst = 1'b1;
    reg pdm_valid = 1'b0;
    reg [CHANNELS-1:0] pdm_bits = 0;
    reg coef_write = 1'b0;
    reg [11:0] coef_address = 0;
    reg signed [17:0] coef_data = 0;
    wire audio_valid;
    wire signed [23:0] audio_sample;

    reg [CHANNELS-1:0] stimulus [0:TICKS-1];
    reg [17:0] weights [0:CHANNELS*TAPS-1];
    integer index;
    integer outputs;
    integer file;

    talker_focus dut (
        .clk(clk),
        .rst(rst),
        .pdm_valid(pdm_valid),
        .pdm_bits(pdm_bits),
        .coef_write(coef_write),
        .coef_address(coef_address),
        .coef_data(coef_data),
        .shift(SHIFT[5:0]),
        .audio_valid(audio_valid),
        .audio_sample(audio_sample)
    );

    always #4 clk = ~clk;

    always @(posedge clk) begin
        if (audio_valid) begin
            $fdisplay(file, "%0d", audio_sample);
            outputs = outputs + 1;
        end
    end

    initial begin
        $readmemh("focus_stimulus.hex", stimulus);
        $readmemh("focus_weights.hex", weights);
        file = $fopen("focus_rtl.txt", "w");
        outputs = 0;
        repeat (4) @(posedge clk);
        rst <= 1'b0;
        for (index = 0; index < CHANNELS * TAPS; index = index + 1) begin
            @(posedge clk);
            coef_write   <= 1'b1;
            coef_address <= index;
            coef_data    <= weights[index];
        end
        @(posedge clk);
        coef_write <= 1'b0;
        for (index = 0; index < TICKS; index = index + 1) begin
            @(posedge clk);
            pdm_valid <= 1'b1;
            pdm_bits  <= stimulus[index];
            @(posedge clk);
            pdm_valid <= 1'b0;
            repeat (TICK_CYCLES - 2) @(posedge clk);
        end
        repeat (TICK_CYCLES * 192 * 2) @(posedge clk);
        $fclose(file);
        $display("outputs %0d", outputs);
        $finish;
    end

endmodule
