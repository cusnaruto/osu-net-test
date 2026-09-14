Trước khi đi vào giải quyết bài toán xây dựng một AI để chơi osu!, trước hết sẽ cần phải hiểu cơ chế của trò chơi, và những dữ liệu ta có thể trích xuất từ nó.
\subsection{Cơ chế}
osu! là một trò chơi nhịp điệu, với yếu tố chủ đạo sẽ là nhắm và bấm lên những hình tròn (HitObject) theo nhịp điệu của bài hát \cite{osu-game-mode}. Thông thường, người chơi của trò chơi này sẽ sử dụng chuột hoặc bảng vẽ điện tử để nhắm, và bàn phím để bấm. Một đặc điểm nổi bật của osu! là toàn bộ các màn chơi, được gọi là “beatmap”, hoàn toàn được tạo ra bởi cộng đồng người chơi  bằng trình chỉnh sửa trong chính trò chơi hoặc công cụ bên ngoài. Điều này mang lại cho cộng đồng khả năng sáng tạo và trải nghiệm những beatmap cực kỳ khó, thuộc hàng thử thách nhất trong thể loại trò chơi nhịp điệu.

\paragraph{Đối tượng}

\begin{figure}[htbp]{Màn hình trò chơi trong một beatmap}
    \centering
    \includegraphics[width=0.75\textwidth]{breakdown.png}
    \label{fig:osu-gameplay-screen}
\end{figure}

Như đã thể hiện ở hình 3.1, người chơi sẽ phải phối hợp giữa tay và mắt để ngắm và nhấn những hình tròn cho thật chính xác nhất.

Trong osu! có ba loại đối tượng người chơi sẽ gặp trong quá trình hoàn thành một beatmap \cite{osu-game-mode}.
\begin{itemize}
    \item Hit circle: Đây là loại đối tượng đơn giản nhất. Gồm một hình tròn rỗng ở ngoài (Approach Circle) và một hình tròn bên trong. Người chơi nhắm chuột tới hình tròn rồi ấn nút. Thời điểm tốt nhất để ấn là khi hình tròn ở ngoài tới gần viền trắng nhất có thể.
        \begin{figure}[H]{Ba hit circles, bấm theo thứ tự 1-2--3}
      \centering
      \includegraphics[width=0.75\textwidth]{hitcircle.png}
      \label{fig:hit-circles}
    \end{figure}
    Trong hình 3.2, đối tượng duy nhất có thể bấm được hiện tại là hit circle số 1, do Approach Circle của nó đã gần chạm hình tròn bên trong, còn 2 hit circle còn lại vẫn còn ở quá xa. Nhìn chung, trong phiên bản osu! này, một hit circle chỉ có thể được bấm sau khi và chỉ khi các hit circle trước nó đã được bấm xong.
    \item Slider: Đối tượng này yêu cầu người chơi nhấn phím tại vòng tròn bắt đầu của slider đúng thời điểm, tương tự như hit circle. Tuy nhiên, thay vì thả phím ngay, người chơi giữ phím và di chuyển theo quả bóng (slider ball) xuất hiện cho đến khi nó đến cuối slider. Một số slider có mũi tên chỉ hướng ngược lại, yêu cầu người chơi theo slider lần nữa theo hướng ngược, điều này có thể lặp lại nhiều lần trong một slider. Trong quá trình di chuyển, người chơi sẽ nhận điểm nhỏ cho mỗi “tick” trên slider. Khi đến cuối slider, người chơi thả phím ra.
    \begin{figure}[H]{Slider với mũi tên ngược}
        \centering
        \includegraphics[width=0.75\textwidth]{slider.png}
        \label{fig:slider-reverse-arrow}
    \end{figure}
    Ở hình 3.3, người chơi sẽ phải nhắm theo một đường thẳng theo slider trên rồi nhắm ngược lại, trong khi phải nhấn giữ phím trong suốt khoảng thời gian trên.
    \item Spinner: Yêu cầu người chơi giữ phím và di chuyển con trỏ xuôi hoặc ngược chiều kim đồng hồ để xoay vòng. Người chơi cần xoay liên tục cho đến khi thanh chỉ báo cho biết spinner đã hoàn thành, nếu không, combo (chuỗi điểm liên tiếp) sẽ bị đặt lại. Nếu người chơi hoàn thành spinner sớm, họ có thể nhận thêm điểm thưởng cho các vòng xoay bổ sung.
    \begin{figure}[H]{Spinner đã được hoàn thành với 40000 điểm thưởng}
        \centering
        \includegraphics[width=0.65\textwidth]{spinner.png}
        \label{fig:spinner-complete}
    \end{figure}
    Mọi spinner trong game sẽ xuất hiện giống như hình 3.4, với sự khác biệt duy nhất là độ dài của nó.
\end{itemize}
\paragraph{Những chỉ số liên quan}

Mỗi beatmap sẽ có một chỉ số đo độ khó, được gọi là Star Rating (SR). SR càng cao thường sẽ có nghĩa là beatmap ấy sẽ càng khó. Nó được ảnh hưởng bởi nhiều yếu tố khác nhau kết hợp lại như khoảng cách giữa những HitObject, mật độ dày đặc của những HitObject, tốc độ di chuyển của slider. Ngoài ra, khi tạo beatmap, người tạo cũng có thể thiết đặt một vài tham số có thể ảnh hưởng tới độ khó như sau:
\begin{itemize}
    \item Circle size (CS): Kích cỡ của hit circle và slider trong beatmap. Càng cao thì chúng sẽ càng bé.
    \item Approach rate (AR): Tốc độ tiếp cận của approach circle. Càng cao thì càng nhanh.
    \item Overall difficulty (OD): Quyết định sự ``chặt chẽ'' của khoảng thời gian được phép bấm hit circle. Càng cao thì người chơi càng cần phải bấm chính xác hơn để có điểm cao.
\end{itemize}
\paragraph{Cách tính điểm}

Trong khoá luận này, thang điểm chính được sử dụng để đo hiệu quả của mô hình sẽ là độ chính xác (Accuracy) \cite{osu-acc}. Độ chính xác trong \textit{osu!} được tính dựa trên việc người chơi nhắm con trỏ đến HitObject rồi bấm chính xác cỡ nào. Trong osu!, mỗi lần người chơi thao tác lên một đối tượng sẽ được hệ thống phán định bằng một mức điểm, thường gọi là judgement. Các mức hit 300, hit 100 và hit 50 không biểu thị số lượng lượt bấm, mà biểu thị chất lượng của một lần thao tác. Hit 300 là mức phán định tốt nhất, cho thấy người chơi nhấn gần đúng thời điểm yêu cầu và con trỏ nằm trong vùng hợp lệ của đối tượng. Hit 100 và hit 50 là các mức phán định thấp hơn, tương ứng với thao tác vẫn được tính là thành công nhưng sai lệch thời gian hoặc vị trí lớn hơn. Miss là trường hợp người chơi không thao tác hợp lệ trong cửa sổ thời gian cho phép, khiến đối tượng bị bỏ lỡ và thường làm đứt chuỗi combo.

Cửa sổ thời gian để đạt các mức 300, 100 và 50 phụ thuộc vào chỉ số Overall Difficulty (OD) của beatmap. Khi Overall Difficulty cao, khoảng thời gian cho phép để đạt phán định tốt sẽ hẹp hơn, khiến người chơi cần nhấn chính xác hơn. Vì vậy, các mức hit này phản ánh trực tiếp chất lượng nhắm và bấm của người chơi, đồng thời là cơ sở để tính độ chính xác tổng thể của lượt chơi.

Đóng góp phần trăm của từng loại hit như sau:

\begin{itemize}
    \item Một hit 300 tương đương \(100\%\) độ chính xác.
    \item Một hit 100 tương đương \(33.\overline{3}\%\) độ chính xác.
    \item Một hit 50 tương đương \(16.\overline{6}\%\) độ chính xác.
    \item Miss tương đương \(0\%\).
\end{itemize}

Do đó, độ chính xác tổng thể có thể được tính qua việc lấy tổng phần trăm đóng góp của tất cả hit, chia cho số lượng hit tối đa có thể đạt được (tức tổng số vật thể):

\[
\text{Accuracy} =
\frac{
100\,N_{300}
+ 33.\overline{3}\,N_{100}
+ 16.\overline{6}\,N_{50}
}{
100\left(
N_{300} + N_{100} + N_{50} + N_{\text{miss}}
\right)
}.
\]

\paragraph{Modifiers}

Modifiers, hay gọi tắt là \textit{mods}, được sử dụng để tăng, giảm độ khó hoặc cung cấp các chức năng đặc biệt trong màn chơi.
\begin{figure}[H]{Hộp thoại lựa chọn mods trong game}
        \centering
        \includegraphics[width=1.0\textwidth]{mods.png}
        \label{fig:mods}
    \end{figure}
Phần lớn các modifiers sẽ có ảnh hưởng đến tổng điểm số mà người chơi nhận được. Một số modifiers trong số này sẽ phù hợp cho việc huấn luyện mô hình hơn một số modifiers khác, chi tiết sẽ được trình bày ở các phần sau. Khoá luận sẽ tập trung vào những modifiers làm tăng độ khó của màn chơi.
\begin{itemize}
  \item {Hard Rock (HR):} Tăng giá trị của Circle Size lên 30\%, khiến các vòng tròn trở nên nhỏ hơn. Ngoài ra, modifier này sẽ đảo ngược vị trí của các HitObject theo chiều dọc và tăng các thiết lập độ khó khác (AR, HP, OD) lên 40\%. Hệ số nhân tổng điểm là $1.06\times$.

  \item {Sudden Death (SD) / Perfect (PF):} Với Sudden Death, người chơi sẽ thất bại ngay lập tức nếu bỏ lỡ một nốt. Perfect nâng mức độ khó cao hơn, khi chỉ cần đạt điểm không hoàn hảo cho một đối tượng cũng sẽ khiến người chơi thất bại. Không có thay đổi về hệ số nhân tổng điểm.

  \item {Double Time (DT) / Nightcore (NC):} Tăng tốc độ của beatmap lên 150\%, khiến thời lượng bài hát ngắn hơn 33\%. Các giá trị AR, HP và OD được tăng nhẹ. Hệ số nhân tổng điểm là $1.12\times$.

  \item {Hidden (HD):} Loại bỏ các vòng tiếp cận (approach circles) và khiến các hit object dần biến mất sau khi xuất hiện một thoáng trên màn hình. Hệ số nhân tổng điểm là $1.06\times$.

  \item {Flashlight (FL):} Giới hạn vùng hiển thị trong quá trình chơi chỉ còn một khu vực nhỏ xung quanh con trỏ. Hệ số nhân tổng điểm là $1.12\times$.
\end{itemize}

\subsection{Mô tả dữ liệu}
Tập dữ liệu khoá luận sử dụng cho việc huấn luyện mô hình sẽ gồm hai loại dữ liệu sau từ trò chơi.

\paragraph{Beatmap}

Beatmap (màn chơi) được cấu thành từ nhiều loại HitObject và thường sẽ bám sát bài nhạc được sử dụng nhất có thể. Beatmap có định dạng đuôi .osu, có thể đọc được bằng trình đọc văn bản. Nó mô tả vị trí của các HitObject, hiệu ứng âm thanh (hitsound), cũng như các hiệu ứng đặc biệt khác. Tệp này cũng bao gồm các thiết lập độ khó và nhiều tham số khác ảnh hưởng trực tiếp đến lối chơi. Thông tin quan trọng nhất mà chúng ta cần chú ý đến là mục HitObjects.
HitObjects chứa thông tin về những đối tượng sẽ xuất hiện, loại đối tượng, và thời điểm mà chúng xuất hiện. Mỗi dòng trong HitObjects được phân tách bằng dấu hai chấm theo cấu trúc:
\[
 [\text{x}, \text{y}, \text{time}, \text{type}, \text{hitSound}, \text{objectParams}, \text{hitSample}] \cite{dot-osu}.
\]
Trong đó, x và y là toạ độ của đối tượng trong cửa sổ trò chơi, time là thời điểm đối tượng cần được thao tác, tính bằng mili-giây kể từ lúc bài hát bắt đầu, type là loại đối tượng. Tuỳ thuộc vào loại đối tượng mà objectParams có được sử dụng hay không. Nếu loại đối tượng là slider, objectParams sẽ có cấu trúc như ở dưới, và được mô tả rõ tại bảng 3.1:
\[
[\text{curveType} \mid \text{curvePoints}, \text{slides}, \text{length}, \text{edgeSounds}, \text{edgeSets}] 
\] 

\begin{table}[H]{Các thuộc tính cấu tạo nên một slider}
\centering
\begin{tabular}{|l|p{0.65\textwidth}|}
\hline
\textbf{Thuộc tính} & \textbf{Mô tả} \\
\hline
\texttt{curveType} & Loại đường cong của slider. Có 4 loại đường cong là: Linear, Bezier, Perfect và Catmull. \\
\hline
\texttt{curvePoints} & Các toạ độ dạng \texttt{x:y} biểu thị điểm xác định hình dạng đường cong của slider. \\
\hline
\texttt{slides} & Số lần lặp của slider. \\
\hline
\texttt{length} & Độ dài của slider tính theo pixel trên màn hình. \\
\hline
\texttt{edgeSounds}, \texttt{edgeSets} & Liên quan tới âm thanh của slider, không quan trọng. \\
\hline
\end{tabular}
\end{table}