import re

class News:
    def __init__(self, header, details):
        self.main_text = header
        self.details = details

    def __str__(self):
        return "{}\n{}".format(self.main_text, "\n\t\t".join(self.details))

    def get_lines_for_document(self):
        details_text = " ".join(self.details)
        return "{} {}".format(self.main_text, details_text)

class Section:
    def __init__(self, title:str, duration:str, text_lines:list[str]):
        self.title = title
        self.duration = duration
        self.text_lines = text_lines
        self.news:list[News] = []
        self._parse_sections()

    def __str__(self):
        return "{}\n{}".format(self.title, "\n".join([str(n) for n in self.news]))

    def _parse_sections(self):
        non_empty_lines = [line for line in self.text_lines if not _is_empty_line(line)]
        section_head_sub_indices = _parse_section_indices(non_empty_lines)
        news_lines = _construct_news_lines_from_indices(non_empty_lines, section_head_sub_indices)
        for news_line in news_lines:
            header_text = _construct_text_from_lines(news_line[0])
            sublines_texts = [_construct_text_from_lines(sublines) for sublines in news_line[1]]
            self.news.append(News(header_text, sublines_texts))
    
    def get_title_for_document(self):
        """
        Return the title by formatting for to be a title 
        for the document in vector store
        """
        return self.title.lower()


class Parser:
    def __init__(self, content: str):
        self.content_lines = [self._clean_lines(line) for line in content.split("\n")]
    
    def _clean_lines(self, line):
        return line.replace("\xa0", " ").replace("\r", "")
        
    def parse_sections(self):
        sections = []

        time_info_lines = [i for i, line in enumerate(self.content_lines) if self._is_section_time_info_line(line)]
        
        for i in range(len(time_info_lines)-1):
            current_time_index = time_info_lines[i]
            next_time_index = time_info_lines[i+1]
            
            current_section_title_index = self._get_preceding_nonempty_string(current_time_index)
            current_text_start_index = self._get_following_nonempty_string(current_time_index)
            current_text_end_index = self._get_preceding_nonempty_string(next_time_index)

            sections.append(Section(
                self.content_lines[current_section_title_index],
                self.content_lines[current_time_index],
                self.content_lines[current_text_start_index:current_text_end_index]
            ))

        # Add the last section
        last_section_title_index = self._get_preceding_nonempty_string(time_info_lines[-1])
        last_section_text_start = self._get_following_nonempty_string(time_info_lines[-1])

        sections.append(Section(
            self.content_lines[last_section_title_index],
            self.content_lines[time_info_lines[-1]],
            self.content_lines[last_section_text_start:]
        ))

        return sections
        
    
    def _get_preceding_nonempty_string(self, index):
        """
        Returns the first line that is not empty and before the index 
        """
        result = index - 1 
        while result > -1 and self.content_lines[result] == "":
            result -= 1
        return result
    
    def _get_following_nonempty_string(self, index):
        """
        Returns the first line that is not empty and after the index 
        """
        result = index + 1 
        while result < len(self.content_lines) and self.content_lines[result] == "":
            result += 1
        return result

    
    def _is_section_time_info_line(self, line):
        """
        Check if a line contains string in the form of 
        d|dd DK d|dd SN
        or 
        d|dd DK
        or 
        d|dd SN
        """
        minutes_seconds_pattern = r'^(?:\d{1,2}\sDK\s\d{1,2}\sSN)$'
        if bool(re.match(minutes_seconds_pattern, line.strip())):
            return True
        
        either_minute_or_secods_pattern = r'^(?:\d{1,2}\s(?:DK|SN))$'
        return bool(re.match(either_minute_or_secods_pattern, line.strip()))



def _parse_section_indices(lines):
    """
    Returns the indices of headline and sublines considering the start character of both
    """
    
    head_line_indices = [i for i,line in enumerate(lines) if _is_headline(line.strip())]
    sub_line_indices = [i for i,line in enumerate(lines) if _is_subline(line.strip())]

    # Some sections consits only subline starts
    # For such, sublines will be treated as headlines
    if len(head_line_indices) == 0 and len(sub_line_indices) > 0:
        head_line_indices.extend(sub_line_indices)
        sub_line_indices.clear()

    # Add final line index for easier iterations
    head_line_indices.append(len(lines)-1)
    # Tuple array to keep sections as (head_line_index, [sub_line_indices])
    section_indices = []

    for i, index in enumerate(head_line_indices[:-1]):
        current_subline_indices = []

        # If sub_line_indices's first element is bigger than next headlines index 
        # that subline belongs to the next section
        while len(sub_line_indices) > 0 and sub_line_indices[0] < head_line_indices[i+1]:
            current_subline_indices.append(sub_line_indices.pop(0))

        section_indices.append((index, current_subline_indices))

    return section_indices

def _construct_news_lines_from_indices(lines, indices):
    """
    Returns the text lines seperated by the different indices
    passed to this function
    """    
    news = []
    
    for i, current_indices in enumerate(indices[:-1]):
        current_news = [[], []]
        headline_index, subline_indices = current_indices
        next_headline_index, _ = indices[i+1]
        
        if len(subline_indices) > 0:
            headline_text = lines[headline_index:subline_indices[0]]
        else:
            headline_text = lines[headline_index:next_headline_index]
        
        current_news[0].extend(headline_text)

        # Make it easier to iterate
        subline_indices.append(next_headline_index)
        for j, subline_index in enumerate(subline_indices[:-1]):
            subline_text = lines[subline_index:subline_indices[j+1]]
            current_news[1].append(subline_text)

        news.append(current_news)

    return news

def _construct_text_from_lines(lines):
    """
    For an item in headline or subline, constructs a text
    consists of its lines seperated by a space
    """
    def clean_line(line):
        stripped_line = line.strip()
        if stripped_line[0] == "•" or stripped_line[0] == "*":
            return stripped_line[1:].strip()
        return stripped_line.strip()

    return " ".join([clean_line(l) for l in lines])


def _is_headline(text: str):
    return text.startswith("•")

def _is_subline(text: str):
    return text.startswith("*")

def _is_empty_line(text: str):
    return text == "" or all([c == ' ' for c in text])
